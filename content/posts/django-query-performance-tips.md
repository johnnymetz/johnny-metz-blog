---
title: 'Django Query Performance Tips'
date: 2023-06-03T21:15:13-04:00
tags:
  - Python
  - Django
  - Pytest
cover:
  image: 'covers/django-racecar.png'
ShowToc: true
draft: true
---

Optimizing Django query performance is critical for building performant web applications. Django provides many tools and methods for optimizing database queries in its [Database access optimization](https://docs.djangoproject.com/en/4.2/topics/db/optimization/) documentation. In this blog post, we will explore some additional tips and tricks I've compiled over the years to help you identify and optimize your slow Django queries.

## Kill Long-Running Queries with a Statement Timeout

PostgreSQL supports a [`statement_timeout`](https://www.postgresql.org/docs/current/runtime-config-client.html#GUC-STATEMENT-TIMEOUT) parameter that allows you to set a maximum time limit per query. This is useful for preventing long-running queries from tying up precious resources and slowing down your application. At [PixieBrix](https://www.pixiebrix.com/), we've seen a few long-running queries cause a full database outage. Setting a statement timeout in your Django settings can help prevent this from happening.

```python
DATABASES = {
    "default": {
        ...
        "OPTIONS": {
            "options": f"-c statement_timeout=30s",
        },
    }
}
```

Now any query that takes longer than 30 seconds will be terminated.

```python
from django.db import connection

with connection.cursor() as cursor:
    cursor.execute("select pg_sleep(31)")
# django.db.utils.OperationalError: canceling statement due to statement timeout
```

A few notes:

- Per the documentation, if `log_min_error_statement` is set to `ERROR` (which is the default), the statement that timed out will also be logged as a [query_canceled](https://www.postgresql.org/docs/current/errcodes-appendix.html#:~:text=57014,query_canceled) error (code `57014`). You should use these logs to identify slow queries.
- PostgreSQL supports setting a database-wide statement timeout, but [the docs don't recommend it](https://www.postgresql.org/docs/current/runtime-config-client.html#:~:text=Setting%20statement_timeout%20in%20postgresql.conf%20is%20not%20recommended%20because%20it%20would%20affect%20all%20sessions.) because it can cause problems with long-running maintenance tasks, such as backups. Instead, it is recommended to set the statement timeout on a per-connection basis as shown above.
- MySQL appears to support a similar [`max_execution_time`](https://dev.mysql.com/doc/refman/8.0/en/optimizer-hints.html#optimizer-hints-execution-time) parameter, but I haven't tested it.
- Statement timeouts may differ across servers. For example, you probably want to set a higher statement timeout on your celery workers than on your web servers. You can do this by conditionally setting the statement timeout:

```python
# https://stackoverflow.com/a/50843002/6611672
IN_CELERY_WORKER = sys.argv and sys.argv[0].endswith("celery") and "worker" in sys.argv

if IN_CELERY_WORKER:
    STATEMENT_TIMEOUT = "1min"
else:
    STATEMENT_TIMEOUT = "30s"
```

## Sanity check query counts in units tests with `assertNumQueries`

When writing unit tests, it's important to ensure that your code is making the expected number of queries. Django provides a convenient method called [`assertNumQueries`](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#django.test.TransactionTestCase.assertNumQueries) that allows you to assert the number of queries made by your code.

```python
class MyTestCase(TestCase)
    def test_something(self):
        with self.assertNumQueries(5)
            # code that makes 5 expected queries
```

If you're using `pytest-django`, then you can use [`django_assert_num_queries`](https://pytest-django.readthedocs.io/en/latest/helpers.html#django_assert_num_queries) to achieve the same functionality.

## Catch N+1 queries with `nplusone`

An N+1 query is a common performance issue that occurs when your code makes too many database queries. The [`nplusone`](https://github.com/jmcarp/nplusone) package detects these bad queries in your code. It works by raising an `NPlusOneError` where a single query is executed repeatedly in a loop. Read more about it in a [previous blog post](https://johnnymetz.com/posts/find-nplusone-violations/).

While `nplusone` is an indispensable tool I use in all of my Django projects, it is important to note that the package is orphaned and does not catch all violations. For example, I've noticed it doesn't work with `.only()` or `.defer()`.

```python
for user in User.objects.defer("email"):
    # This should raise an NPlusOneError but it doesn't
    email = user.email
```

Because of these shortcomings, it is important to use other optimization techniques alongside `nplusone`.

## Catch N+1 queries with `django-zen-queries`

The [`django-zen-queries`](https://github.com/dabapps/django-zen-queries) package allows you to control which parts of your code are permitted to run queries. It includes a `queries_disabled()` context manager / decorator that raises a `QueriesDisabledError` exception when a query is executed inside it. You can use it to prevent unnecessary queries on prefetched objects, or to ensure that queries are only called when they are needed. I use it to fill in the gaps where `nplusone` falls short.

For example, as outlined in the previous section, `nplusone` won't catch the following N+1 query, but `django-zen-queries` will.

```python
from zen_queries import fetch, queries_disabled

# The fetch function forces evaluation of the queryset, which is
# necessary before entering the queries_disabled context
qs = fetch(User.objects.defer("email"))

with queries disabled():
    for user in qs:
        # Raises a QueriesDisabledError exception
        email = user.email
```

## Fix N+1 queries with vanilla Python

Most sections above help you pinpoint N+1 queries in your code. But how do you fix them?

One approach I frequently employ is to use vanilla Python on prefetched objects, instead of Django queryset methods, to prevent making new and unnecessary database queries.

For instance, consider the following code:

```python
for user in User.objects.prefetch_related("groups"):
    # BAD: N+1 query
    first_group = user.groups.first()

    # GOOD: Does not make a new query
    first_group = user.groups.all()[0]
```

`qs.first()` makes a new query to the database, whereas `qs.all()[0]` does not.

Here are some more examples:

| Django                           | Python                                    |
| -------------------------------- | ----------------------------------------- |
| `qs.values_list("x", flat=True)` | `[obj.x for obj in qs.all()]`             |
| `qs.values("x")`                 | `[{"x": obj.x} for obj in qs.all()]`      |
| `qs.order_by("x", "y")`          | `sorted(qs, lambda obj: (obj.x, obj.y))`  |
| `qs.filter(x=1)`                 | `[obj for obj in qs.all() if obj.x == 1]` |
| `qs.exclude(x=1)`                | `[obj for obj in qs.all() if obj.x != 1]` |

Note, the `nplusone` package should catch all of these N+1 violations so be sure to use it to catch these issues.

## Prevent fetching large, unused fields with `defer()`

Some fields, such as `JSONField` and `TextField`, require expensive processing to convert to Python objects. This slows down queries, especially when dealing with querysets containing a few thousand instances or more. You can use `defer()` to prevent fetching these fields and improve query performance.

```python
class Book(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    pub_date = models.DateField()
    notes = models.JSONField()

books = Book.objects.defer("content", "notes")
```

Alternatively, you can use the `only()` method to explicitly specify the fields you want to include in the query result.

```python
books = Book.objects.only("title", "pub_date")
```

However, in situations where you want to exclude specific large fields, using `defer()` often results in more concise and efficient code.

## Avoid using `distinct()` on large fields

The `distinct()` method eliminates duplicate objects from a queryset by comparing all values across the result set. When applied to large fields, such as `JSONField` and `TextField`, the database needs to perform expensive comparisons, which can lead to slower query execution times.

To mitigate this issue, you can limit the scope of `distinct()` by applying it to a subset of fields.

The best option is employ the previous tip and use `defer()` to exclude large fields entirely.

```python
Book.objects.filter(<filter-that-generates-duplicates>).defer("content", "notes").distinct()
```

On PostgreSQL only, another option is to pass fields as positional arguments via `distinct(*fields)`. This tells the database to only compare the specified fields. Ideally you should use the primary key field, but any unique field will work.

```python
Book.objects.filter(<filter-that-generates-duplicates>).distinct("id")
```

## Conclusion

In conclusion, query performance is the crux of any Django web application. Use these tips and tricks to help you identify and fix slow Django queries and make your applications more efficient.

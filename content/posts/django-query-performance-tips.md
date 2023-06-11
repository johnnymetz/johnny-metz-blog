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

Optimizing Django query performance is critical for building performant web applications. Django provides many tools and methods for optimizing database queries in its [Database access optimization](https://docs.djangoproject.com/en/4.2/topics/db/optimization/) documentation. In this blog post, we will explore some additional tips and tricks I've compiled over the years to help you optimize your Django queries even further.

## Set a Statement Timeout

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

- Per the documentation, if `log_min_error_statement` is set to `ERROR` (which is the default), the statement that timed out will also be logged as a [query_canceled](https://www.postgresql.org/docs/current/errcodes-appendix.html#:~:text=57014,query_canceled) error (code `57014`). You can use this to identify slow queries and optimize them.
- PostgreSQL supports setting a database-wide statement timeout, but the docs don't recommend it because it can cause problems with long-running maintenance tasks, such as backups. Instead, it is recommended to set the statement timeout on a per-connection basis as shown above.
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

## Use `assertNumQueries` in unit tests

When writing unit tests, it's important to ensure that your code is making the expected number of queries. Django provides a convenient method called [`assertNumQueries`](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#django.test.TransactionTestCase.assertNumQueries) that allows you to assert the number of queries made by your code.

```python
class MyTestCase(TestCase)
    def test_something(self):
        with self.assertNumQueries(5)
            # code that makes 5 expected queries
```

If you're using `pytest-django`, then you can use [`django_assert_num_queries`](https://pytest-django.readthedocs.io/en/latest/helpers.html#django_assert_num_queries) to achieve the same functionality.

## Use `nplusone` to catch N+1 queries

An N+1 query is a common performance issue that can occur when your code makes too many database queries. Learn about it [here](https://johnnymetz.com/posts/find-nplusone-violations/).

The [`nplusone`](https://github.com/jmcarp/nplusone) package detects N+1 queries in your code. It works by raising an `NPlusOneError` where a single query is executed repeatedly in a loop, resulting in unnecessary database access. I recommend using it only in your test suite - read about how to implement that [here](https://johnnymetz.com/posts/find-nplusone-violations/#nplusone).

While `nplusone` is a useful tool, it is important to note that the package is orphaned and does not catch all violations. For example, I've noticed it doesn't work with `.only()` or `.defer()`.

```python
for user in User.objects.defer("email"):
    # This should raise an NPlusOneError but it doesn't
    email = user.email
```

Because of these shortcomings, it is important to use other optimization techniques alongside `nplusone`.

## Use `django-zen-queries` to catch N+1 queries

The [`django-zen-queries`](https://github.com/dabapps/django-zen-queries) package allows you to control which parts of your code are allowed to run queries and which aren't. You can use it to prevent unnecessary queries on prefetched objects, or to ensure that queries are only executed when they are needed. I use it on code that the `nplusone` package won't catch.

For example, as outlined in the previous section, `nplusone` won't catch the following N+1 query, but `django-zen-queries` will.

```python
from zen_queries import fetch, queries_disabled

qs = fetch(User.objects.defer("email"))

with queries disabled():
    for user in qs:
        # Raises a `zen_queries.QueriesDisabledError` exception
        email = user.email
```

## Use vanilla Python to prevent new queries

When working with prefetched objects, it's important to avoid making new queries that could slow down your application. Instead of using Django queryset methods, you can use vanilla Python to optimize your queries and improve performance.

For instance, consider the following code:

```python
for user in User.objects.prefetch_related("groups"):
    # BAD: N+1 query
    first_group = user.groups.first()

    # GOOD: Does not make a new query
    first_group = user.groups.all()[0]
```

Here are some more examples:

| Django                           | Python                                    |
| -------------------------------- | ----------------------------------------- |
| `qs.values_list("x", flat=True)` | `[obj.x for obj in qs.all()]`             |
| `qs.values("x")`                 | `[{"x": obj.x} for obj in qs.all()]`      |
| `qs.order_by("x", "y")`          | `sorted(qs, lambda obj: (obj.x, obj.y))`  |
| `qs.filter(x=1)`                 | `[obj for obj in qs.all() if obj.x == 1]` |
| `qs.exclude(x=1)`                | `[obj for obj in qs.all() if obj.x != 1]` |

Note, the `nplusone` package should catch all of these N+1 violations so be sure to use it in conjunction with this approach.

## Use `defer()` to prevent fetching large, unused fields

Some fields, such as `JSONField` and `TextField`, require expensive processing to convert to Python objects. This slows down queries, especially when dealing with querysets containing a few thousand instances or more. You can use `defer()` to prevent fetching these fields and improve query performance.

```python
class Book(models.Model):
    title = models.CharField(max_length=255)
    content = models.TextField()
    pub_date = models.DateField()
    rating = models.IntegerField()
    notes = models.JSONField()

books = Book.objects.defer("content", "notes")
```

Alternatively, you can use the `only()` method to explicitly specify the fields you want to include in the query result.

```python
books = Book.objects.only("title", "pub_date", "rating")
```

However, in situations where you want to exclude specific large fields, using `defer()` often results in more concise and efficient code.

## Conclusion

In conclusion, query performance is the crux of any Django web application. Use these tips and tricks to further optimize your Django queries and make your applications more efficient.

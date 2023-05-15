---
title: 'Django Query Performance Tips'
date: 2023-06-03T21:15:13-04:00
tags:
  - Python
  - Django
  - Pytest
cover:
  image: 'covers/django-sonic.png'
ShowToc: true
draft: true
---

Optimizing Django query performance is critical for building performant web applications. Django provides many tools and methods for optimizing database queries in its [Database access optimization](https://docs.djangoproject.com/en/4.2/topics/db/optimization/) documentation. In this blog post, we will explore some additional tips and tricks I've compiled over the years to help you optimize your Django queries even further.

## Use `assertNumQueries` in unit tests

When writing unit tests, it's important to ensure that your code is making the expected number of queries. Django provides a convenient method called [`assertNumQueries`](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#django.test.TransactionTestCase.assertNumQueries) that allows you to assert the number of queries made by your code. If you're using `pytest-django`, which I recommend, then you can use [`django_assert_num_queries`](https://pytest-django.readthedocs.io/en/latest/helpers.html#django_assert_num_queries) to achieve the same functionality.

```python
def test_db_access(django_assert_num_queries):
    with django_assert_num_queries(3):
        # code that makes 3 expected queries
```

## Use `nplusone` to catch N+1 queries

N+1 queries are a common performance issue that can occur when your code makes too many database queries. Learn about it [here](https://johnnymetz.com/posts/find-nplusone-violations/).

The [`nplusone`](https://github.com/jmcarp/nplusone) package detects N+1 queries in your code. It works by raising an `NPlusOneError` where a single query is executed repeatedly in a loop, resulting in unnecessary database access. I recommend using it only in your test suite - read about how to implement that [here](https://johnnymetz.com/posts/find-nplusone-violations/#nplusone).

While `nplusone` is a useful tool, it is important to note that the package is orphaned and does not catch all violations. For example, I've noticed it doesn't work with `.only()` or `.defer()`.

```python
for user in User.objects.defer("email"):
    # This should raise an NPlusOneError but it doesn't
    email = user.email
```

Because of these shortcomings, it is important to use other optimization techniques in conjunction with `nplusone`.

## Use `django-zen-queries` to catch N+1 queries

The [`django-zen-queries`](https://github.com/dabapps/django-zen-queries) package allows you to control which parts of your code are allowed to run queries and which aren't. You can use it to prevent unnecessary queries on prefetched objects, or to ensure that queries are only executed when they are needed. I use it on code that the `nplusone` package won't catch.

For example, `nplusone` won't catch the following N+1 query but `django-zen-queries` will.

```python
from zen_queries import fetch, queries_disabled

qs = fetch(User.objects.defer("email"))

with queries disabled():
    for user in qs:
        # Raises a `zen_queries.QueriesDisabledError` exception
        email = user.email
```

## Set Statement Timeout in Postgres

- https://stackoverflow.com/questions/19963954/set-transaction-query-timeout-in-psycopg2
- https://www.crunchydata.com/blog/exposing-postgres-performance-secrets
- https://postgresqlco.nf/doc/en/param/statement_timeout/
- https://medium.com/squad-engineering/configure-postgres-statement-timeouts-from-within-django-6ce4cd33678a

## Use Python to prevent new queries

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

## Use `only()` or `defer()` to prevent fetching large, unused fields

Some fields, such as `JSONField` and `TextField`, can consume a lot of memory and be very slow to load into a Django object, especially when dealing with querysets containing a few thousand objects or more. You can use `only()` or `defer()` to prevent fetching these fields and improve query performance.

## Conclusion

In conclusion, query performance is the crux of any Django web application. Use these tips and tricks to further optimize your Django queries and make your applications more efficient.

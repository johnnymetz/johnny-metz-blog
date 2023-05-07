---
title: 'Django Query Performance Tips'
date: 2023-06-03T21:15:13-04:00
tags:
  - Python
  - Django
cover:
  image: 'covers/django-sonic.png'
ShowToc: true
draft: true
---

Optimizing Django query performance is critical for building performant web applications. Django provides many tools and methods for optimizing database queries, but there are some tips and tricks that are not listed in the [Database access optimization](https://docs.djangoproject.com/en/4.2/topics/db/optimization/) documentation. In this blog post, we will explore some of these tips and tricks to help you optimize your Django queries even further.

## Use `assertNumQueries` in unit tests

When writing unit tests, it's important to ensure that your code is making the expected number of queries. Django provides a convenient method called [`assertNumQueries`](https://docs.djangoproject.com/en/4.2/topics/testing/tools/#django.test.TransactionTestCase.assertNumQueries) that allows you to assert the number of queries made by your code. If you're using pytest-django, you can use [`django_assert_num_queries`](https://pytest-django.readthedocs.io/en/latest/helpers.html#django_assert_num_queries) to achieve the same functionality.

```python
def test_db_access(self):
    with self.assertNumQueries(3):
        # code that makes 3 expected queries
```

## Use `nplusone` to catch N+1 queries

The N+1 problem is a common performance issue that arises when your code makes too many database queries. Learn about it [here](https://johnnymetz.com/posts/find-nplusone-violations/).

The [`nplusone`](https://github.com/jmcarp/nplusone) package detects N+1 queries in your code. It is a fantastic backstop and has uncovered countless N+1 queries in my own code. We recommend using it only in your test suite - read about how to implement that [here](https://johnnymetz.com/posts/find-nplusone-violations/#nplusone).

Note the package is orphaned and doesn't catch all violations. For example, I've noticed it doesn't work with `.only()` or `.defer()`. The following code is an N+1 query but `nplusone` doesn't catch it:

```python
for user in User.objects.defer("email"):
    email = user.email
```

## Use `django-zen-queries` to catch N+1 queries

The [`django-zen-queries`](https://github.com/dabapps/django-zen-queries) package allows you to control which parts of your code are allowed to run queries and which aren't. You can use it to prevent unnecessary queries on prefetched objects, or to ensure that queries are only executed when they are needed. I use it on code that the `nplusone` package won't catch.

For example, `nplusone` won't catch the following N+1 query but `django-zen-queries` will raise a `zen_queries.QueriesDisabledError` exception:

```python
from zen_queries import fetch, queries_disabled

qs = fetch(User.objects.defer("email"))

with queries disabled():
    for user in qs:
        email = user.email
```

## Use Python to prevent new queries on prefetched objects

When you've prefetched objects, you don't want to make new queries on those objects. You can use vanilla Python, instead of Django queryset methods, to prevent new queries.

For example:

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

Note, the `nplusone` package should catch all of these N+1 violations.

## Use `only()` or `defer()` to prevent fetching large, unused fields

Some fields, such as `JSONField` and `TextField`, can consume a lot of memory and be very slow to load into a Django object, especially when dealing with querysets containing a few thousand objects or more. You can use `only()` or `defer()` to prevent fetching these fields and improve query performance.

In conclusion, query performance is the crux of any Django web application. Use these tips and tricks to further optimize your Django queries and make your applications more efficient.

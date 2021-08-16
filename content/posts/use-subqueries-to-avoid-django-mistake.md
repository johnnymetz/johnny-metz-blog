---
# Use Subqueries to prevent a common Django mistake/pitfall/blunder
# Common Django ORM Gotcha: SQL Order of Execution
title: 'Use Subqueries to avoid a common Django mistake'
date: 2021-06-21T11:56:09-07:00
description: 'Avoid a common Django pitfall by remembering the SQL order of execution and using Subqueries'
type: 'posts'
tags:
  - Python
  - Django
---

The Django ORM is a powerful tool but I often see developers forget the SQL order of execution, leading to a common mistake. Let's look at an example:

```python
class Book(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "edition"],
                name="%(app_label)s_%(class)s_unique_name_edition",
            )
        ]

    name = models.CharField(max_length=255)
    edition = models.CharField(max_length=255)
    release_year = models.PositiveIntegerField(null=True)
```

I want to write a query that reads:

> Out of the latest books, give me the ones with a non-null release year.

My first attempt might be:

```python
Book.objects.order_by("name", "-edition")
.distinct("name")
.filter(release_year__isnull=False)
```

This seems like a sound approach. Let's test this out using the following sample data:

| Name        | Edition | Release Year |
| ----------- | ------- | ------------ |
| Django tips | 1       | 2020         |
| Django tips | 2       | 2022         |
| Django tips | 3       | null         |
| Golf swings | 1       | 2018         |
| Golf swings | 2       | 2021         |

We're using `pytest` and `pytest-django`.

```python
import pytest
from pytest_django.asserts import assertQuerysetEqual

def test_queryset():
    book1 = Book.objects.create(name="Django tips", edition=1, release_year=2020)
    book2 = Book.objects.create(name="Django tips", edition=2, release_year=2022)
    book3 = Book.objects.create(name="Django tips", edition=3, release_year=None)
    book4 = Book.objects.create(name="Golf swings", edition=1, release_year=2018)
    book5 = Book.objects.create(name="Golf swings", edition=2, release_year=2021)

    qs = (
      Book.objects.order_by("name", "-edition")
      .distinct("name")
      .filter(release_year__isnull=False)
    )
    assertQuerysetEqual(qs, [book5])
```

This fails by returning `[book2, book5]`. We can see the raw SQL using `qs.query`, which looks something like this:

```sql
SELECT DISTINCT ON (name) * FROM core_book
WHERE release_year IS NOT NULL
ORDER BY name ASC, edition DESC;
```

The `WHERE` clause appears _before_ the `ORDER BY` clause, which produces a completely different query that reads:

> Out of the books with a release year, give me the latest ones.

Unfortunately, we can't just simply swap the clauses. The [SQL Order of Execution](https://www.sisense.com/blog/sql-query-order-of-operations/) guarentees `WHERE` clauses are executed before `ORDER BY` clauses.

So how can we fix this? The answer is using SQL Subqueries.

```python
Book.objects.filter(
    id__in=Book.objects.order_by("name", "-edition").distinct("name").values_list("id", flat=True),
    release_year__isnull=False,
)
```

Here, we're using two different queries to fetch our result:

1. Get the latest books.
2. Out of the latest books, give me the ones with a non-null release year.

Note, you don't actually need `.values_list("id", flat=True)`. Django will automatically return just the `id` field when a queryset is used in a subquery. (TODO: check this, maybe link it in the code)

Here's our updated test:

```python
def test_queryset():
    ...

    qs = Book.objects.filter(
        id__in=Book.objects.order_by("name", "-edition").distinct("name"),
        release_year__isnull=False,
    )
    assertQuerysetEqual(qs, [book5])
```

The test passes!

In conclusion, subqueries are a great mechanism for writing fast and complex queries. Check out Django's documentation [here](https://docs.djangoproject.com/en/dev/ref/models/expressions/#subquery-expressions) for more examples.

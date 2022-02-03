---
title: 'Why you need to use Subqueries in Django'
date: 2021-07-21T11:56:09-07:00
tags:
  - Python
  - Django
  - Pytest
  - SQL
cover:
  image: 'covers/django-sql.png'
---

The Django ORM is a powerful tool but certain aspects of it are counterintuitive, such as the SQL order of execution.

Let's look at an example of this trap and how we can fix it using subqueries:

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

This seems like a sound approach. Note we're PostgreSQL because it's the only database that supports `distinct(*fields)` ([docs](https://docs.djangoproject.com/en/3.2/ref/models/querysets/#distinct)).

Let's test this out using the following sample data:

| Name        | Edition | Release Year       |
| ----------- | ------- | ------------------ |
| Django tips | 1       | 2020               |
| Django tips | 2       | 2022               |
| Django tips | 3       | null (coming soon) |
| Golf swings | 1       | 2018               |
| Golf swings | 2       | 2021               |

We're writing our unit test in `pytest` and `pytest-django`. Our query should return just the last record, `book5`.

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

This test fails because the queryset returns `[book2, book5]`. We can see the raw SQL using `qs.query`, which looks something like this:

```sql
SELECT DISTINCT ON (name) * FROM core_book
WHERE release_year IS NOT NULL
ORDER BY name ASC, edition DESC;
```

The `WHERE` clause appears _before_ the `ORDER BY` clause, which produces a completely different query that reads:

> Out of the books with a non-null release year, give me the latest ones.

Unfortunately, we can't just simply swap the clauses. The [SQL order of execution](https://www.sisense.com/blog/sql-query-order-of-operations/) guarentees `WHERE` clauses are executed before `ORDER BY` clauses.

So how can we fix this? The answer is using SQL subqueries.

```python
Book.objects.filter(
    id__in=Book.objects.order_by("name", "-edition").distinct("name").values_list("id", flat=True),
    release_year__isnull=False,
)
```

Here, we're using two different queries to fetch our result:

1. Get the latest books.
2. Out of the latest books, give me the ones with a non-null release year.

Note, you don't actually need `.values_list("id", flat=True)`. Django will automatically return just the `id` field when a queryset is used in a subquery.

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

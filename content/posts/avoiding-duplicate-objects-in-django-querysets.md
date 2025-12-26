---
title: 'Avoiding Duplicate Objects in Django Querysets'
date: 2025-12-26T00:00:00-07:00
tags:
  - Python
  - Django
  - SQL
ShowToc: true
cover:
  image: 'covers/django.png'
---

When filtering Django querysets across relationships, you can easily end up with duplicate objects in your results. This is a common gotcha that happens with both one-to-many (1:N) and many-to-many (N:N) relationships. Let's explore why this happens and the best way to avoid it.

## The Problem

When you filter a queryset by traversing a relationship, Django performs a SQL JOIN. If a parent object has multiple related objects that match your filter, the parent object appears multiple times in the result set.

Let's look at a concrete example with a one-to-many relationship:

```python
class Author(models.Model):
    name = models.CharField(max_length=255)

class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(Author, on_delete=models.CASCADE, related_name='books')
```

Here's what the database tables might look like:

**Author Table**

| id  | name    |
| --- | ------- |
| 1   | Charlie |
| 2   | Alice   |
| 3   | Zoe     |

**Book Table**

| id  | title   | author_id |
| --- | ------- | --------- |
| 1   | Book A  | 1         |
| 2   | Book B  | 2         |
| 3   | Book C  | 2         |
| 4   | Novel D | 3         |

If we want to find all authors who have written books whose titles start with "Book":

```python
Author.objects.filter(books__title__startswith="Book")
# [<Author: Charlie>, <Author: Alice>, <Author: Alice>]
```

Notice that Alice appears twice in the result set. This happens because when Django executes the query, it performs a JOIN across the relationship:

| author_id | name    | book_id | title  |
| --------- | ------- | ------- | ------ |
| 1         | Charlie | 1       | Book A |
| 2         | Alice   | 2       | Book B |
| 2         | Alice   | 3       | Book C |

Since Alice wrote both "Book B" and "Book C", the JOIN produces two rows for her. The same issue occurs with many-to-many relationships — if an object belongs to multiple groups that match your filter, the object will appear multiple times.

## Common Solutions (and Their Problems)

### Using `distinct()`

The most straightforward solution is to use `distinct()`:

```python
Author.objects.filter(books__title__startswith="Book").distinct()
# [<Author: Charlie>, <Author: Alice>]
```

This works, but can be expensive. `distinct()` compares all selected fields to determine uniqueness, which is problematic if your model has large fields like `JSONField` or `TextField`. The database has to compare all these fields for every row, which can kill performance on large datasets.

### Using `distinct(*fields)` (PostgreSQL only)

PostgreSQL supports `DISTINCT ON` specific fields, which is more efficient than comparing all fields. You can use any unique field (typically `id`):

```python
Author.objects.filter(books__title__startswith="Book").distinct("id")
# [<Author: Charlie>, <Author: Alice>]
```

This only compares the specified unique field, avoiding the performance issues with large fields. However, `distinct(*fields)` has several limitations and gotchas (see [Django documentation](https://docs.djangoproject.com/en/6.0/ref/models/querysets/#django.db.models.query.QuerySet.distinct) and [PostgreSQL documentation](https://www.postgresql.org/docs/current/sql-select.html#SQL-DISTINCT)). The most notable is that you can't easily order by other fields. PostgreSQL requires that `SELECT DISTINCT ON` expressions match the initial `ORDER BY` expressions. For example, if you try to do:

```python
Author.objects.filter(books__title__startswith="Book")
.order_by("name")
.distinct("id")
```

You'll get this error:

```
django.db.utils.ProgrammingError: SELECT DISTINCT ON expressions must match initial ORDER BY expressions
```

A workaround is to use a subquery to get the distinct objects, then filter by those objects:

```python
subquery = Author.objects.filter(books__title__startswith="Book").distinct("id")
Author.objects.filter(id__in=subquery).order_by("name")
# [<Author: Alice>, <Author: Charlie>]
```

This solves the ordering problem, but it's verbose and requires two separate queries (though Django optimizes this into a subquery). It's also not immediately clear what's happening when reading the code.

## The Best Solution: `Exists` Subquery

The cleanest and most performant solution is to use an `Exists` subquery:

```python
from django.db.models import Exists, OuterRef

Author.objects.filter(
    Exists(
        Book.objects.filter(
            author=OuterRef("id"),
            title__startswith="Book",
        )
    )
).order_by("name")
# [<Author: Alice>, <Author: Charlie>]
```

1. **Performance**: `Exists` stops evaluation as soon as it finds a matching row, making it very efficient. Per the [Django documentation](https://docs.djangoproject.com/en/stable/ref/models/expressions/#exists-subqueries):

   > Exists is a Subquery subclass that uses an SQL EXISTS statement. In many cases it will perform better than a subquery since the database is able to stop evaluation of the subquery when a first matching row is found.

2. **No ordering restrictions**: Unlike `distinct(*fields)`, you can order by any field without issues.

3. **Clear intent**: The code clearly expresses "find authors who have books whose titles start with 'Book'" without the complexity of subqueries or distinct operations.

4. **Works everywhere**: This solution works with all databases, not just PostgreSQL.

May your Django querysets be duplicate-free and fast.

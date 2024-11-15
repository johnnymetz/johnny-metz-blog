---
title: '5 Ways to Get the Latest Book Per Author in Django'
date: 2024-11-14T12:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/books-stacked.png'
---

In a Django application, fetching the latest record for each group is a common yet challenging task, especially when working with large datasets. Whether you're building an analytics dashboard or managing grouped data, finding an efficient solution is key. In this blog post, we’ll explore five different approaches to tackle this problem, ranked from least to most effective based on performance and readability, using the following `Book` model:

```python
class Book(models.Model):
    title = models.CharField(max_length=255)
    author = models.ForeignKey(
        Author, on_delete=models.CASCADE, related_name="books"
    )
    genre = models.CharField(max_length=255)
    published_at = models.DateTimeField()
    is_featured = models.BooleanField(default=False)
```

## Solution 1: Python Max with Prefetch

```python
latest_books = [
    max(author.books.all(), key=lambda x: x.published_at, default=None)
    for author in Author.objects.prefetch_related("books")
]
```

Performs heavy computation in Python rather than leveraging the database, which is [bad for performance](https://docs.djangoproject.com/en/5.1/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python). Also makes two database queries (better solutions do it in one).

## Solution 2: Prefetch with Ordered QuerySet

```python
from django.db.models import Prefetch

latest_books = [
    author.books.first()
    for author in Author.objects.prefetch_related(
        Prefetch("books", queryset=Book.objects.order_by("-published_at")),
    )
]
```

Similar to the first solution but performs the sorting in the database, which is more efficient.

## Solution 3: Subquery

```python
from django.db.models import OuterRef, Subquery

authors_with_latest_book_id = Author.objects.annotate(
    latest_book_id=Subquery(
        Book.objects.filter(author=OuterRef("id"))
        .order_by("-published_at")
        .values("id")[:1]
    )
)
```

Fetches the latest book per author in a single query. But only returns the book ID, so we'd need to make another query to get the full book object if needed.

## Solution 4: Alias Max

```python
from django.db.models import F, Max

latest_books = (
    Book.objects
    .alias(latest_published_at=Max("author__books__published_at"))
    .filter(published_at=F("latest_published_at"))
)
```

The least intuitive approach. Issues a `GROUP BY ... HAVING ...` query under the hood. Note we're using [`alias`](https://docs.djangoproject.com/en/5.1/ref/models/querysets/#alias) instead of [`annotate`](https://docs.djangoproject.com/en/5.1/ref/models/querysets/#annotate) because we don't need the `latest_published_at` field in the result.

## Solution 5: Postgres DISTINCT ON

```python
latest_books = Book.objects.order_by("author", "-published_at").distinct("author")
```

The best / most concise approach but only available in Postgres. Leverages its [DISTINCT ON](https://neon.tech/postgresql/postgresql-tutorial/postgresql-distinct-on) clause to get the latest book per author in a single query.

To show how elegant this solution is, let's say we want to fetch the latest featured book per author and genre group:

```python
latest_books = (
    Book.objects.filter(is_featured=True)
    .order_by("author", "genre", "-published_at")
    .distinct("author", "genre")
)
```

May your Django queries be fast and clean.

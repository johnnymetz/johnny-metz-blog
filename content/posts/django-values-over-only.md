---
title: 'Speed Up Django Queries with values() over only()'
date: 2025-06-29T13:11:26-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

If your Django queries feel slow, the problem might not be your database — it might be your ORM. Recently, I was working with a query that took 25 seconds to run through the Django ORM, but the underlying SQL completed in just 2 seconds. With a single change, I got the ORM query down to 2 seconds as well — and reduced the memory footprint by 70%.

Let's walk through what happened, and why using `.values()` instead of `.only()` can dramatically improve performance.

## The Setup

In our actual application, the schema was more complex. But to keep this post focused on the performance insight, we'll use a simplified example: querying a large number of `Book` records and pulling fields from related `Author` and `Publisher` models.

The original queryset used `.select_related()` and `.only()` to limit the fields we pulled in:

```python
books = (
    Book.objects.filter(published_at__year=2025)
    .select_related("author__publisher")
    .only(
        "title",
        "published_at",
        "author__first_name",
        "author__publisher__name",
    )
)
```

This returned ~240,000 records, but took 25 seconds to run.

## The Optimized Version

Swapping `.only()` for `.values()` dropped the runtime to just 2 seconds:

```python
from django.db.models import F

books = (
    Book.objects.filter(published_at__year=2025)
    .values(
        "title",
        "published_at",
        author_name=F("author__name"),
        publisher_name=F("author__publisher__name"),
    )
)
```

Same number of records, same fields — 10× faster.

## Why the Speedup?

The key difference is how Django handles the result set:

|                           | `.select_related()` + `.only()` | `.values()`           |
| ------------------------- | ------------------------------- | --------------------- |
| Model instantiation       | Yes                             | No                    |
| Python-level overhead     | High (full objects)             | Low (plain dicts)     |
| Speed for large querysets | Slow (25s in our case)          | Fast (2s in our case) |
| Memory size of result set | 43 MB                           | 13 MB                 |

Even when using `.only()`, Django still instantiates full model objects — including related models pulled in with `.select_related()`. This means more memory usage and more work at the Python level. In contrast, `.values()` skips all of that and returns plain dictionaries, which is significantly faster and lighter for large querysets.

## Takeaway

Django's ORM is powerful, but not cheap. For large read-only datasets such as API responses and analytics exports, reach for `.values()`.

May your Django queries be fast and lean.

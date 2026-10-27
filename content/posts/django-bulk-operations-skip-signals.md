---
title: 'Stop Django Bulk Operations From Silently Skipping Signals'
date: 2026-10-26T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
draft: true
---

Django's `bulk_create()`, `bulk_update()`, and `update()` are fast because they skip `save()`. That also means they skip the `pre_save` and `post_save` signals. It's documented for [`bulk_create()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-create), [`bulk_update()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-update), and [`update()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#update), but nothing warns you at runtime. If a signal invalidates a cache, writes an audit log, or syncs a search index, one bulk call quietly leaves that data stale. This post shows how to make those calls fail loudly instead.

## The Footgun

Say a receiver keeps a search index in sync whenever a book is saved:

```python
class Book(models.Model):
    title = models.CharField(max_length=255)
    price = models.DecimalField(max_digits=6, decimal_places=2)
    publisher = models.ForeignKey(Publisher, null=True, on_delete=models.SET_NULL)

@receiver(post_save, sender=Book)
def index_book(sender, instance, **kwargs):
    search_index.upsert(instance)
```

Saving a single book works:

```python
book.price = 10
book.save()  # ✅ Reindexed
```

The bulk equivalents don't:

```python
Book.objects.filter(pk=book.pk).update(price=10)  # ❌ Search shows old price
Book.objects.bulk_create(books)                   # ❌ New books not searchable
Book.objects.bulk_update(books, ["price"])        # ❌ Search shows old prices
```

There's no error and no warning. Search results drift from the database until someone notices. It's also easy to introduce: in code review, swapping a loop of `save()` calls for one `update()` looks like a performance win, not a bug.

## Make It Loud

Override the three methods on a custom queryset and raise unless the caller explicitly opts out:

```python
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models

_skip_signals = ContextVar("skip_signals", default=False)

@contextmanager
def skip_signals():
    token = _skip_signals.set(True)
    try:
        yield
    finally:
        _skip_signals.reset(token)

class SignalSafeQuerySet(models.QuerySet):
    def bulk_create(self, *args, **kwargs):
        self._check("bulk_create")
        return super().bulk_create(*args, **kwargs)

    def bulk_update(self, *args, **kwargs):
        self._check("bulk_update")
        return super().bulk_update(*args, **kwargs)

    def update(self, **kwargs):
        self._check("update")
        return super().update(**kwargs)

    def _check(self, method):
        if not _skip_signals.get():
            raise RuntimeError(
                f"{self.model.__name__}.{method}() skips signals. "
                "Use save() or wrap it in skip_signals()."
            )
```

Attach it to every model whose signals do real work, as both the default and the [base manager](https://docs.djangoproject.com/en/6.1/topics/db/managers/#base-managers):

```python
class Book(models.Model):
    ...
    objects = SignalSafeQuerySet.as_manager()

    class Meta:
        base_manager_name = "objects"
```

The base manager matters because Django runs some writes through it instead of `objects`, and they skip signals too:

- `publisher.book_set.add(book)` sets the foreign key with `Book._base_manager.update()`.
- Deleting a publisher nulls `Book.publisher` (`on_delete=models.SET_NULL`) the same way.

By default the base manager is a plain `Manager`, so neither write is caught. Pointing it at `objects` makes both raise. [`m2m_changed`](https://docs.djangoproject.com/en/6.1/ref/signals/#m2m-changed) can't help here; it only fires for `ManyToManyField`.

Now the bulk call fails the first time it runs, ideally in your test suite rather than in production:

```python
>>> Book.objects.filter(pk=book.pk).update(price=10)
RuntimeError: Book.update() skips signals. Use save() or wrap it in skip_signals().
```

Everything that fires signals keeps working:

- `save()`, `create()`, `get_or_create()`, and `update_or_create()` all go through `save()`, which uses Django's internal `_update()` rather than the public `update()`.
- `delete()` already sends `pre_delete` and `post_delete` for each row.

You also get a couple of things for free:

- The async variants (`aupdate()`, `abulk_create()`, and `abulk_update()`) call their sync counterparts, so they're blocked too.
- With a custom `through` model, `book.tags.add(tag)` inserts rows with `bulk_create()`. Give the through model a `SignalSafeQuerySet` and many-to-many writes are covered as well.

## Opting Out

Sometimes you need the bulk speed, like a backfill that touches a million rows. Wrap the call:

```python
with skip_signals():
    Book.objects.filter(publisher=publisher).update(price=F("price") * 0.9)
```

Use it sparingly. Every `skip_signals()` block is a place where search indexes, caches, or anything else driven by signals won't update. The upside is that each one is now an explicit, searchable decision that shows up in code review.

## What It Doesn't Cover

This guards the ORM, not the database. Raw SQL and data migrations still skip signals.

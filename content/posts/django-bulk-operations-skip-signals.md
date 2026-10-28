---
title: 'Stop Django Bulk Operations From Silently Skipping Signals'
date: 2026-10-27T12:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django-runtime-error.png'
---

Django's `bulk_create()`, `bulk_update()`, and `update()` are fast because they skip `save()`. That also means they skip the `pre_save` and `post_save` signals, so your receivers never fire. It's documented for [`bulk_create()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-create), [`bulk_update()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#bulk-update), and [`update()`](https://docs.djangoproject.com/en/6.1/ref/models/querysets/#update), but nothing warns you at runtime. If a signal invalidates a cache, writes an audit log, or syncs a search index, one bulk call quietly skips that critical work. This post shows how to make those calls fail loudly instead.

## The Footgun

Say a receiver keeps a search index in sync whenever a book is saved:

```python
class Book(models.Model):
    title = models.CharField(max_length=255)
    publisher = models.ForeignKey(Publisher, null=True, on_delete=models.SET_NULL)

@receiver(post_save, sender=Book)
def index_book(sender, instance, **kwargs):
    search_index.upsert([instance.pk])
```

Saving a single book works:

```python
book.title = "Dune Messiah"
book.save()  # ✅ Reindexed
```

The bulk equivalents don't:

```python
Book.objects.bulk_create(books)                               # ❌ New books not searchable
Book.objects.bulk_update(books, ["title"])                    # ❌ Search shows old titles
Book.objects.filter(pk=book.pk).update(title="Dune Messiah")  # ❌ Search shows old title
```

There's no error and no warning. Search results drift from the database until something resyncs them. It's also easy to introduce: in code review, swapping a loop of `save()` calls for one `update()` looks like a performance win, not a bug.

## Make It Loud

Add a guardrail: override the three methods on a custom queryset and raise unless the caller explicitly opts out:

```python
from contextlib import contextmanager
from contextvars import ContextVar

from django.db import models

_allow_signal_skipping = ContextVar("allow_signal_skipping", default=False)

@contextmanager
def allow_signal_skipping():
    token = _allow_signal_skipping.set(True)
    try:
        yield
    finally:
        _allow_signal_skipping.reset(token)

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
        if not _allow_signal_skipping.get():
            raise RuntimeError(
                f"{self.model.__name__}.{method}() skips signals. "
                "Use save() or wrap it in allow_signal_skipping()."
            )
```

Attach it to every model whose signals do real work, as both the [default manager](https://docs.djangoproject.com/en/6.1/topics/db/managers/#default-managers) and the [base manager](https://docs.djangoproject.com/en/6.1/topics/db/managers/#base-managers):

```python
class Book(models.Model):
    ...
    objects = SignalSafeQuerySet.as_manager()

    class Meta:
        base_manager_name = "objects"
```

The base manager matters because Django runs a few internal writes through it instead of `objects` (the same kind of blind spot as [reads that skip custom managers](https://johnnymetz.com/posts/django-custom-managers-data-leak/)), and they skip `post_save` too:

```python
publisher.book_set.add(book)  # ❌ Reverse foreign key add()
publisher.delete()            # ❌ on_delete=SET_NULL
```

- A [reverse foreign key `add()`](https://docs.djangoproject.com/en/6.1/ref/models/relations/#django.db.models.fields.related.RelatedManager.add) moves the book with one `Book._base_manager.update()` instead of `save()`.
- Deleting a publisher sets `publisher` to `NULL` on its books the same way.

The base manager is a plain `Manager` by default, so neither write is caught. Pointing it at `objects` makes both raise. Just make sure `objects` [doesn't filter rows](https://docs.djangoproject.com/en/6.1/topics/db/managers/#don-t-filter-away-any-results-in-this-type-of-manager-subclass).

Now the bulk call fails loudly:

```python
>>> Book.objects.filter(pk=book.pk).update(title="Dune Messiah")
RuntimeError: Book.update() skips signals. Use save() or wrap it in allow_signal_skipping().
```

Everything that fires signals keeps working:

- `save()`, `create()`, `get_or_create()`, and `update_or_create()` all go through `save()`.
- `delete()`, on an instance or a queryset, already sends `pre_delete` and `post_delete` for each row.

The async variants (`aupdate()`, `abulk_create()`, and `abulk_update()`) call their sync counterparts, so they're blocked for free.

The same goes for a custom many-to-many `through` model with its own receivers: `book.tags.add(tag)` inserts its rows with `bulk_create()`, so giving the through model a `SignalSafeQuerySet` makes `add()` raise too.

## Opting Out

Sometimes you need the bulk speed, like a backfill that trims whitespace from a million titles. Wrap the call:

```python
with allow_signal_skipping():
    Book.objects.update(title=Trim("title"))
```

The two base manager writes need different handling. A reverse foreign key `add()` has a signal-safe mode, so it needs no bypass:

```python
publisher.book_set.add(book, bulk=False)  # ✅ Calls save() per book
```

Deletes do, every time: Django runs the `SET_NULL` update even when the publisher has no books. Run the receiver's logic for the affected books yourself:

```python
book_ids = list(publisher.book_set.values_list("pk", flat=True))
with allow_signal_skipping():
    publisher.delete()
search_index.upsert(book_ids)
```

Bypass sparingly. Every `allow_signal_skipping()` block is a place where search indexes, caches, or anything else driven by signals won't update. The upside is that each one is now an explicit, searchable decision that shows up in code review.

## What It Doesn't Cover

This guards the ORM, not the database. Raw SQL and data migrations (which use [historical models](https://docs.djangoproject.com/en/6.1/topics/migrations/#historical-models)) still skip signals.

Covering every write path means moving the side effect into the database itself, such as a trigger that queues changed rows in an outbox table for a worker to process. Most databases support triggers, and on Postgres, [django-pgtrigger](https://github.com/AmbitionEng/django-pgtrigger) lets you define them alongside your models. However, that's more complex and lives far from your app code. If your bulk writes go through the ORM, the queryset guard is the better trade-off.

Discuss: [Reddit](https://www.reddit.com/r/django/comments/1xhefcs/stop_django_bulk_operations_from_silently/)

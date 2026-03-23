---
title: 'Django Custom Managers Are Silently Leaking Data'
date: 2026-02-16T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

[Django custom managers](https://docs.djangoproject.com/en/6.0/topics/db/managers/#custom-managers) are a common way to exclude rows by default, such as inactive or soft-deleted rows. However, they aren't applied consistently, which leads to unintended data exposure. This post covers where that happens and how to fix it.

## The Setup

Let's model stores and products with a soft-deletable relationship:

```python
class Store(models.Model):
    name = models.CharField(max_length=255)

class Product(models.Model):
    name = models.CharField(max_length=255)

class StoreProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)

class StoreProduct(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    objects = StoreProductManager()  # default: active only
    all_objects = models.Manager()   # escape hatch: everything
```

The custom manager is declared first, making it the [default manager](https://docs.djangoproject.com/en/6.0/topics/db/managers/#default-managers). That feels like it should protect us everywhere, but it doesn't.

## The Rule

> Managers only run for the model you're querying — not joined models.

If the queryset is rooted in `StoreProduct`, the manager runs. If `StoreProduct` is only pulled in via a join, it doesn't.

## Queries That Work

Multiple core query patterns behave correctly and exclude inactive rows because Django is building the query from `StoreProduct`:

| Pattern          | Example                                              |
| ---------------- | ---------------------------------------------------- |
| Direct query     | `StoreProduct.objects.all()`                         |
| Reverse relation | `store.storeproduct_set.all()`                       |
| Prefetch         | `Store.objects.prefetch_related("storeproduct_set")` |

`prefetch_related` is the interesting one. It looks like a join, but Django actually runs a separate query and stitches the results together in Python. Since that separate query is rooted in `StoreProduct`, the manager fires.

## Queries That Break and How to Fix Them

### ManyToManyField Access

```python
class Store(models.Model):
    name = models.CharField(max_length=255)
    products = models.ManyToManyField("Product", through="StoreProduct")

# ❌ Includes inactive rows
store.products.all()
```

This query is built from the `Product` model. `StoreProduct` is used as a join condition, so its manager never runs.

The fix is to replace the `ManyToManyField` with queryset methods that duplicate the manager logic (i.e., remove inactive records):

```python
class StoreQuerySet(models.QuerySet):
    def for_product(self, product):
        return self.filter(
            storeproduct__product=product,
            storeproduct__active=True,
        )

class ProductQuerySet(models.QuerySet):
    def for_store(self, store):
        return self.filter(
            storeproduct__store=store,
            storeproduct__active=True,
        )

class Store(models.Model):
    objects = StoreQuerySet.as_manager()

class Product(models.Model):
    objects = ProductQuerySet.as_manager()

# ✅ Excludes inactive rows
Store.objects.for_product(product)
Product.objects.for_store(store)
```

### Filtering Across Relations

```python
# ❌ Includes inactive rows
Store.objects.filter(storeproduct__product=product)
```

This query is rooted in `Store`. Same problem and same fix: use the queryset method.

```python
# ✅ Excludes inactive rows
Store.objects.for_product(product)
```

### Aggregations & Annotations

```python
# ❌ Includes inactive rows
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

Again, the query targets `Store`. The fix is to explicitly filter out inactive records:

```python
# ✅ Excludes inactive rows
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## Catching Leaks

These bugs are easy to miss and nothing breaks loudly. Inactive records just quietly show up in your results.

The best safety net is to automatically surface unsafe queries. The following snippet is a lightweight runtime check that inspects SQL and raises an error if any query touches the `StoreProduct` table without filtering on `active`:

```python
import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

_query_check_enabled = ContextVar("_query_check_enabled", default=True)
_original_fetch_all = QuerySet._fetch_all

TABLE_NAME = StoreProduct._meta.db_table
TABLE_REF = re.compile(
    rf"(?:FROM|JOIN)\s+{re.escape(TABLE_NAME)}(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+\d+))?",
    re.IGNORECASE,
)

def active_filter_for(ref: str):
    return re.compile(rf"\b{ref}\.active(?!,)\b", re.IGNORECASE)

class StoreProductQueryError(AssertionError):
    def __init__(self, sql: str):
        super().__init__(f"Missing active filter on StoreProduct: {sql}")

def enable_query_check():
    def check(self):
        if not _query_check_enabled.get():
            return _original_fetch_all(self)
        try:
            # Remove quotes to simplify matching
            sql = str(self.query).replace('"', "").replace("'", "")
        # Queries guaranteed to return no rows (e.g., .none()) raise EmptyResultSet
        except EmptyResultSet:
            return _original_fetch_all(self)

        refs = Counter(m.group("alias") or TABLE_NAME for m in TABLE_REF.finditer(sql))
        for ref, count in refs.items():
            if len(active_filter_for(ref).findall(sql)) < count:
                raise StoreProductQueryError(sql=sql)

        return _original_fetch_all(self)

    QuerySet._fetch_all = check

@contextmanager
def disable_query_check():
    token = _query_check_enabled.set(False)
    try:
        yield
    finally:
        _query_check_enabled.reset(token)
```

Enable it in your tests suite (e.g., pytest `conftest.py`) to detect leaks before they reach production.

## When You Actually Want Inactive Data

Sometimes you need everything — analytics dashboards, admin tooling, audit logs. Make it explicit:

```python
with disable_query_check():
    StoreProduct.all_objects.all()
```

---

If you use custom managers to filter data, I'd bet this pitfall is affecting you. Understand the rule, add the runtime check, and fix the leaks. A manager that doesn't run isn't protecting anything.

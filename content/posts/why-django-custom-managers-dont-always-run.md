---
title: 'Prevent Django Custom Managers from Leaking Data'
date: 2026-02-16T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

[Django custom managers](https://docs.djangoproject.com/en/6.0/topics/db/managers/#custom-managers) are a common way to exclude records by default, such as inactive or soft-deleted records. However, they aren't applied consistently, which leads to unintended data exposure. This post covers where that happens and how to fix it.

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

    # Default: exclude inactive rows
    objects = StoreProductManager()

    # Escape hatch: include everything
    all_objects = models.Manager()
```

We declare the custom manager first so it becomes the [default manager](https://docs.djangoproject.com/en/6.0/topics/db/managers/#default-managers). That feels like it should protect us everywhere, but it doesn't.

## Queries That Work

The rule is:

> Custom managers are only applied to the target model — not across joins.

These patterns correctly use the custom manager and exclude inactive rows because the target model is `StoreProduct`:

| Pattern          | Example                                              |
| ---------------- | ---------------------------------------------------- |
| Direct query     | `StoreProduct.objects.all()`                         |
| Reverse relation | `store.storeproduct_set.all()`                       |
| Prefetch         | `Store.objects.prefetch_related("storeproduct_set")` |

Prefetch issues a second query whose queryset is on `StoreProduct` (it loads related rows via that model's manager, not by joining StoreProduct into the main Store query), so the custom manager still applies.

## Queries That Break and How to Fix Them

These patterns bypass the custom manager and include inactive rows because they do NOT target the `StoreProduct` model.

The fix is to explicitly exclude inactive rows (essentially duplicating what the custom manager does).

### ManyToManyField Access

```python
class Store(models.Model):
    name = models.CharField(max_length=255)
    products = models.ManyToManyField("Product", through="StoreProduct")

# ❌ Includes inactive records
store.products.all()
```

This query targets the `Product` model, so it never touches the through model's manager.

The best solution is to replace the `ManyToManyField` with custom queryset methods that explicitly filter on `active`:

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

# ✅ Excludes inactive records
Store.objects.for_product(product)
Product.objects.for_store(store)
```

### Filtering Across Relations

```python
# ❌ Includes inactive records
Store.objects.filter(storeproduct__product=product)
```

This query targets the `Store` model with a join to the through table for the condition.

Use the fix from the previous section:

```python
# ✅ Excludes inactive records
Store.objects.for_product(product)
```

### Aggregations / Annotations

```python
# ❌ Includes inactive records
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

Same issue: The query targets the `Store` model.

We need to explicitly filter out inactive rows:

```python
# ✅ Excludes inactive records
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## Catching Leaks Automatically

These bugs are easy to miss. The safest approach is to catch them programmatically.

Below is a lightweight runtime check that inspects SQL and ensures any query touching `StoreProduct` also filters on `active`.

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

Enable it in tests (e.g., pytest `conftest.py`), and any unsafe query will fail.

## When You Do Want Inactive Data

For analytics, auditing, or admin flows, you may need full access:

```python
with disable_query_check():
    StoreProduct.all_objects.all()
```

Make this explicit — it should never happen accidentally.

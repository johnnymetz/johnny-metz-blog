---
title: "Why Django Custom Managers Don't Always Run And How to Fix the Leaks"
date: 2026-02-16T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

[Django custom managers](https://docs.djangoproject.com/en/6.0/topics/db/managers/#custom-managers) are a common way
to exclude inactive or soft-deleted records by default. But custom managers aren't used everywhere, leading to unexpected results. This post walks through where it happens and how to fix it.

## The Setup

Suppose we have stores and products linked through a many-to-many style relationship. We use a through model `StoreProduct` with an `active` flag so we can deactivate links without deleting them:

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

    objects = StoreProductManager()
    all_objects = models.Manager()
```

Some notes:

- The first manager declared is the default, which is used in several key query patterns (see the next section and the [Django documentation](https://docs.djangoproject.com/en/6.0/topics/db/managers/#default-managers)); so it needs to be `StoreProductManager`.
- We use `all_objects` when we explicitly need inactive records, including analytics, admin and auditing workflows.

## Queries that Use the Custom Manager

Many common query patterns correctly use the custom manager and exclude inactive records:

| Label           | Query                                                            | Why                                     |
| --------------- | ---------------------------------------------------------------- | --------------------------------------- |
| Direct query    | `StoreProduct.objects.all()`                                     | Explicitly uses the custom manager      |
| Relation access | `store.storeproduct_set.all()`, `product.storeproduct_set.all()` | Uses the `StoreProduct` default manager |
| Prefetch        | `Store.objects.prefetch_related("storeproduct_set")`             | Uses the `StoreProduct` default manager |

## Queries that Do Not Use the Custom Manager

Several query patterns bypass the custom manager and include inactive rows.

### Accessing via ManyToManyField

```python
class Store(models.Model):
    name = models.CharField(max_length=255)
    products = models.ManyToManyField("Product", through="StoreProduct")


# ❌ Bypasses custom manager
store.products.all()
```

The M2M query skips the through model's custom manager entirely.

The best solution is to remove the M2M field and add queryset methods on each end of the relationship that explicitly filter on `active`:

```python
class StoreQuerySet(models.QuerySet):
    def for_product(self, product):
        return self.filter(
            storeproduct__product=product,
            storeproduct__active=True,
        )


class Store(models.Model):
    name = models.CharField(max_length=255)

    objects = StoreQuerySet.as_manager()
```

Create the same pattern for the other direction and then you can use the following queries to fetch all stores for a product and all products for a store, respectively:

```python
Store.objects.for_product(product)
Product.objects.for_store(store)
```

### Filtering across the relation

```python
# ❌ Bypasses custom manager
Store.objects.filter(storeproduct__product=product)
```

Django builds the join directly from the relationship and never invokes custom manager. Use the fix from the previous section: `Store.objects.for_product(product)`

### Annotating across the relation

```python
# ❌ Bypasses custom manager
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

Again, the Django ORM doesn't use the custom manager, which means the annotations include inactive rows. We need to explicitly filter out inactive rows:

```python
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## Automated Check to Catch Leaks

These bypasses are easy to miss so I wrote an automated check that hooks into query execution and asserts that any query accessing the `StoreProduct` table also includes a corresponding `active` filter.

```python
import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

_original_fetch_all = QuerySet._fetch_all
_active_filter_check_enabled = ContextVar("_active_filter_check_enabled", default=True)

TABLE_NAME = StoreProduct._meta.db_table
TABLE_REF = re.compile(
    rf"(?:FROM|JOIN)\s+{re.escape(TABLE_NAME)}(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+\d+))?",
    re.IGNORECASE,
)

def active_filter_for(ref: str):
    return re.compile(rf"\b{ref}\.active(?!,)\b", re.IGNORECASE)

class ActiveFilterMissingError(AssertionError):
    def __init__(self, sql: str):
        super().__init__(f"Query joins StoreProduct without active filter.\n\n{sql}")

def enable_active_filter_query_check():
    def check(self):
        if not _active_filter_check_enabled.get():
            return _original_fetch_all(self)
        try:
            # Remove all quotes to simplify regex matching
            sql = str(self.query).replace('"', "").replace("'", "")
        except EmptyResultSet:
            return _original_fetch_all(self)
        ref_counts = Counter(x.group("alias") or TABLE_NAME for x in TABLE_REF.finditer(sql))
        for ref, count in ref_counts.items():
            matches = active_filter_for(ref).findall(sql)
            if len(matches) < count:
                raise ActiveFilterMissingError(sql=sql)
        return _original_fetch_all(self)

    QuerySet._fetch_all = check

@contextmanager
def disable_active_filter_query_check():
    token = _active_filter_check_enabled.set(False)
    try:
        yield
    finally:
        _active_filter_check_enabled.reset(token)
```

I run the check in my test suite by calling `enable_active_filter_query_check()` at test startup (e.g., in a pytest `conftest.py` autouse fixture). You can also enable this in production by logging instead of raising and creating an alert on that.

Comment about the two implementations (sql regex and query inspection) and when you should use each.

Sometimes you need inactive data: analytics, internal dashboards, auditing. Use `disable_active_filter_query_check` to
opt out:

```python
with disable_active_filter_query_check():
    StoreProduct.all_objects.all()
```

## Conclusion

Django custom managers don't apply to relation lookups, annotations, or aggregates. To avoid leaks:

1. Use queryset methods like `for_product()` and `for_store()` instead of raw relation filters.
2. Filter first (e.g. `filter(storeproduct__active=True)`) before annotating across the relation.
3. Run an automated check in tests (or production) to catch leaks.
4. Use `all_objects` and `disable_active_filter_query_check()` when you intentionally need inactive records.

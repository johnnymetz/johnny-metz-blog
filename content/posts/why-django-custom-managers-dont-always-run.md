---
title: "Why Django Custom Managers Don't Always Run—And How to Fix the Leaks"
date: 2026-02-16T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

Django custom managers are a common way to [modify a manager's initial queryset](https://docs.djangoproject.com/en/6.0/topics/db/managers/#modifying-a-manager-s-initial-queryset), such as excluding inactive or soft-deleted records by default. But custom managers aren't used everywhere — some query paths bypass them entirely leading to unexpected data leaks. This post walks through where it happens and how to fix it.

## The Setup

Suppose we have stores and products linked through a many-to-many style relationship. We use a through model `StoreProduct` with an `active` flag so we can deactivate links without deleting them:

```python
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

We want to exclude inactive records by default and use `all_objects` only when we explicitly need them (analytics, admin, etc.).

We intentionally avoid `ManyToManyField(through="StoreProduct")`. That would bypass the through model and its manager when traversing the relationship. Instead, we use ForeignKeys so `store.storeproduct_set` and `product.storeproduct_set` go through `StoreProduct` and its default manager.

## Queries that Use the Custom Manager

Most common query patterns correctly use the custom manager and exclude inactive records:

| Label           | Query                                                            |
| --------------- | ---------------------------------------------------------------- |
| Direct query    | `StoreProduct.objects.all()`                                     |
| Relation access | `store.storeproduct_set.all()`, `product.storeproduct_set.all()` |
| Prefetch        | `Store.objects.prefetch_related("storeproduct_set")`             |

## Queries that Do Not Use the Custom Manager

The problem appears when you query through the relation from the other side — filters, annotations, and aggregates that join to `StoreProduct` never invoke its custom manager. Django builds the join directly from the relationship.

When you filter across the relation, `Store.objects.filter(storeproduct__product=product)` includes inactive rows because the join doesn't filter on `active`.

Annotations and aggregates show the same bypass. When you annotate or aggregate through the relation:

```python
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

The join for `Count` and `Min` includes inactive rows. Relation lookups are easier to spot; annotations are easy to miss.

For relation lookups, add queryset methods that explicitly filter on `active`:

```python
class StoreQuerySet(models.QuerySet):
    def for_product(self, product):
        return self.filter(
            storeproduct__product=product,
            storeproduct__active=True,
        )

# Usage: Store.objects.for_product(product)
```

`Store.objects.for_product(product)` generates SQL that includes `AND storeproduct.active`:

```sql
SELECT * FROM store
INNER JOIN storeproduct ON store.id = storeproduct.store_id
WHERE storeproduct.product_id = 1 AND storeproduct.active;
```

Same pattern for the other direction: `Product.objects.for_store(store)` with `storeproduct__active=True`.

For annotations, add the `filter` parameter to each aggregation:

```python
from django.db.models import Count, Min, Q

Store.objects.annotate(
    product_count=Count("storeproduct", filter=Q(storeproduct__active=True)),
    first_product_added=Min("storeproduct__created_at", filter=Q(storeproduct__active=True)),
)
```

Or filter first when you only care about stores with at least one active product:

```python
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## Catching Leaks: An Automated Check

Because these bypasses are easy to miss, I run an automated check in my test suite. Two approaches work: validate the generated SQL with regex, or introspect Django's query AST. The SQL regex approach is simpler but database-specific; the introspection approach walks `query.alias_map` and the WHERE tree and is database-agnostic but more complex. Below is the SQL regex implementation in a single file:

```python
import re
from collections import Counter
from contextlib import contextmanager
from contextvars import ContextVar

from django.core.exceptions import EmptyResultSet
from django.db.models.query import QuerySet

from core.models import StoreProduct

_original_fetch_all = QuerySet._fetch_all
_active_filter_check_enabled = ContextVar("_active_filter_check_enabled", default=True)
TABLE_NAME = StoreProduct._meta.db_table

TABLE_REF = re.compile(
    rf"(?:FROM|JOIN)\s+{re.escape(TABLE_NAME)}(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+\d+))?",
    re.IGNORECASE,
)


def active_filter_for(ref: str):
    return re.compile(rf"\b{re.escape(ref)}\.active(?!,)\b", re.IGNORECASE)


class ActiveFilterMissingError(AssertionError):
    def __init__(self, sql: str):
        self.sql = sql.strip()
        super().__init__(f"Query joins StoreProduct without active filter.\n\n{self.sql}")


@contextmanager
def disable_active_filter_query_check():
    token = _active_filter_check_enabled.set(False)
    try:
        yield
    finally:
        _active_filter_check_enabled.reset(token)


def enable_active_filter_query_check():
    def check(self):
        if not _active_filter_check_enabled.get():
            return _original_fetch_all(self)
        try:
            sql = str(self.query).replace('"', "").replace("'", "")
        except EmptyResultSet:
            return _original_fetch_all(self)
        refs = Counter(m.group("alias") or TABLE_NAME for m in TABLE_REF.finditer(sql))
        for ref, count in refs.items():
            matches = active_filter_for(ref).findall(sql)
            if len(matches) < count:
                raise ActiveFilterMissingError(sql=sql)
        return _original_fetch_all(self)

    QuerySet._fetch_all = check
```

Call `enable_active_filter_query_check()` at test startup (e.g., in a pytest `conftest.py` autouse fixture). Any query that joins `StoreProduct` without filtering on `active` fails the test. If excluding inactive data is critical, you can enable this in production and log or alert instead of raising.

## When You Want Inactive Records

Sometimes you need inactive data: analytics, internal dashboards, auditing. Use `disable_active_filter_query_check` to opt out:

```python
with disable_active_filter_query_check():
    list(StoreProduct.all_objects.all())
    list(Store.objects.filter(storeproduct__product=product))  # no active filter
```

The context manager uses a `ContextVar`, so it's thread-safe and scoped to the block.

## Conclusion

Django custom managers don't apply to relation lookups, annotations, or aggregates. To avoid leaks:

1. Use queryset methods like `for_product()` and `for_store()` instead of raw relation filters.
2. Add the `filter` parameter to annotations that traverse the relation.
3. Run an automated check in tests (or production) to catch leaks.
4. Use `all_objects` and `disable_active_filter_query_check()` when you intentionally need inactive records.

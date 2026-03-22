---
title: 'Your Django Custom Manager is Leaking Data'
date: 2026-02-16T00:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

[Django custom managers](https://docs.djangoproject.com/en/6.0/topics/db/managers/#custom-managers) are a common way
to exclude records by default, such as inactive or soft-deleted records. However, custom managers aren't used in all
queries, which leads to unexpected results and data leaks. This post covers where that happens and how to fix it.

## The Setup

Suppose we have stores and products linked through a many-to-many style relationship.

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

    # Use objects when we don't want inactive records.
    objects = StoreProductManager()

    # Use all_objects when we want inactive records.
    all_objects = models.Manager()
```

We use a through model `StoreProduct` with an `active` flag so we can deactivate links without deleting them.

We use a customer manager `StoreProductManager` to exclude inactive records and declare it first so it's
the [default manager](https://docs.djangoproject.com/en/6.0/topics/db/managers/#default-managers), which means it's used
in several key query patterns.

## Queries that Use the Custom Manager

Many common query patterns predictably use the custom manager and exclude inactive records:

| Label           | Query                                                            | Why                                |
| --------------- | ---------------------------------------------------------------- | ---------------------------------- |
| Direct query    | `StoreProduct.objects.all()`                                     | Explicitly uses the custom manager |
| Relation access | `store.storeproduct_set.all()`, `product.storeproduct_set.all()` | Uses the default manager           |
| Prefetch        | `Store.objects.prefetch_related("storeproduct_set")`             | Uses the default manager           |

## Queries that Do Not Use the Custom Manager

Several query patterns bypass the custom manager and include inactive rows.

### Accessing via ManyToManyField

```python
class Store(models.Model):
    name = models.CharField(max_length=255)
    products = models.ManyToManyField("Product", through="StoreProduct")

# ❌ Includes inactive records
store.products.all()
```

The M2M query skips the through model's custom manager entirely.

The best solution is to remove the M2M field and add queryset methods on each end of the relationship that explicitly
filter on `active`:

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

Create the same pattern for the other direction and then you can use the following queries to fetch all stores for a
product and all products for a store, respectively:

```python
# ✅ Excludes inactive records
Store.objects.for_product(product)
Product.objects.for_store(store)
```

### Filtering across the relation

```python
# ❌ Includes inactive records
Store.objects.filter(storeproduct__product=product)
```

Django builds the join directly from the relationship and never invokes the custom manager. Use the fix from the
previous section:

```python
# ✅ Excludes inactive records
Store.objects.for_product(product)
```

### Annotating across the relation

```python
# ❌ Includes inactive records
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

Again, the Django ORM doesn't use the custom manager, which means the annotations include inactive rows. We need to
explicitly filter out inactive rows:

```python
# ✅ Excludes inactive records
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## Automated Check to Catch Leaks

These bypasses are easy to miss so I recommend an automated check that hooks into query execution and checks that any
query accessing the `StoreProduct` table also includes a corresponding `active` filter.

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
        super().__init__(f"Query referenced StoreProduct without active filter: {sql}")

def enable_query_check():
    def check(self):
        if not _query_check_enabled.get():
            return _original_fetch_all(self)
        try:
            # Remove all quotes to simplify regex matching.
            sql = str(self.query).replace('"', "").replace("'", "")
        # Queries guaranteed to return no rows (e.g., .none()) raise EmptyResultSet.
        except EmptyResultSet:
            return _original_fetch_all(self)
        refs = Counter(m.group("alias") or TABLE_NAME for m in TABLE_REF.finditer(sql))
        for ref, count in refs.items():
            matches = active_filter_for(ref).findall(sql)
            if len(matches) < count:
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

I run the check in my test suite by calling `enable_query_check()` at test startup (e.g., in a pytest
`conftest.py` autouse fixture). Now any query accessing the `StoreProduct` table without an `active` filter will raise an error:

```python
StoreProduct.all_objects.all()
# StoreProductQueryError: Query referenced StoreProduct without active filter: SELECT * FROM storeproduct
```

You can also enable this in production by logging instead of raising and creating an
alert on that.

The SQL-regex approach inspects the compiled SQL string, so it stays aligned with what actually hits the database and is
quick to wire up. Inspecting the underlying Django Query object is an alternative solution that may be better if you're
working with multiple databases, instead of writing up regex patterns for multiple database dialects.

Sometimes you need inactive data (analytics, internal dashboards, auditing). Use `disable_active_filter_query_check` to
opt out:

```python
with disable_query_check():
    StoreProduct.all_objects.all()
```

May your queries always return the data you expect.

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

Django custom managers are a common way to exclude inactive or soft-deleted records by default. The catch: custom managers aren't used everywhere. Some query paths bypass them entirely, and inactive data can leak through when you least expect it. This post walks through where it happens and how to fix it.

## The Setup — A Through Model With a Custom Manager

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

The goal: exclude inactive records by default, and use `all_objects` only when we explicitly need them (analytics, admin, etc.).

We intentionally avoid `ManyToManyField(through="StoreProduct")`. That would bypass the through model and its manager when traversing the relationship. Instead, we use ForeignKeys so `store.storeproduct_set` and `product.storeproduct_set` go through `StoreProduct` and its default manager.

## Where the Custom Manager Is Used

Most common query patterns correctly use the custom manager:

- **Direct queries:** `StoreProduct.objects.all()` — uses `StoreProductManager`, so only active rows are returned.
- **Reverse relations:** `store.storeproduct_set.all()` — the reverse FK uses the related model's default manager, so only active links appear.
- **Prefetch:** `Store.objects.prefetch_related("storeproduct_set")` — prefetch uses the default manager, so inactive links are excluded.

## The First Gap — Relation Lookups

The problem appears when you filter across the relation from the other side:

```python
Store.objects.filter(storeproduct__product=product)
```

This query does _not_ use `StoreProduct`'s manager. Django builds a join directly from the relationship; it never calls `StoreProduct.objects.get_queryset()`. Here's the SQL:

```sql
SELECT * FROM store
INNER JOIN storeproduct ON store.id = storeproduct.store_id
WHERE storeproduct.product_id = 1;
```

There is no `AND storeproduct.active = true`. Inactive `StoreProduct` rows are included, so you can get stores you didn't intend.

The fix: add a queryset method that explicitly filters on `active`:

```python
class StoreQuerySet(models.QuerySet):
    def for_product(self, product):
        return self.filter(
            storeproduct__product=product,
            storeproduct__active=True,
        )

# Usage: Store.objects.for_product(product)
```

Same pattern for the other direction: `Product.objects.for_store(store)` with `storeproduct__active=True`. This is a [known Django limitation](https://code.djangoproject.com/ticket/26393) — the manager's queryset isn't used when filtering through relations. Others have hit it too ([example](https://stackoverflow.com/questions/65710627/is-it-possible-to-override-filter-lookup-with-predefined-values-with-custom-mana)).

## More Gaps — Annotations and Aggregates

Other query patterns also bypass the manager. Annotations that join through `StoreProduct` don't use its manager:

```python
Store.objects.annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

The join for `Count` and `Min` includes inactive rows. These are harder to spot than relation lookups.

The most reliable way to catch them is a runtime check. You can either introspect the Django queryset or validate the generated SQL with regex. The SQL approach checks that whenever the `StoreProduct` table appears in a join, the query includes a filter on `active`:

```python
# Pattern 1: find table references (FROM/JOIN {table} [alias])
TABLE_REF = re.compile(
    rf"(?:FROM|JOIN)\s+{re.escape(TABLE_NAME)}(?:\s+(?:AS\s+)?(?P<alias>[A-Z]+\d+))?",
    re.IGNORECASE,
)

# Pattern 2: find ref.active in filter context
def active_filter_for(ref: str):
    return re.compile(rf"\b{re.escape(ref)}\.active(?!,)\b", re.IGNORECASE)

def check(self):
    # ... for each table reference, require matching active filter ...
    if len(matches) < count:
        raise ActiveFilterMissingError(sql=sql)
```

I hook this into `QuerySet._fetch_all` and run it in my test suite. When a query joins `StoreProduct` without filtering on `active`, the tests fail. If excluding inactive data is critical, you can also enable this in production and log (or alert) instead of raising.

The fix for the annotation query:

```python
from django.db.models import Count, Min, Q

Store.objects.annotate(
    product_count=Count("storeproduct", filter=Q(storeproduct__active=True)),
    first_product_added=Min("storeproduct__created_at", filter=Q(storeproduct__active=True)),
)
```

Or filter first when you only care about stores that have at least one active product:

```python
Store.objects.filter(storeproduct__active=True).annotate(
    product_count=Count("storeproduct"),
    first_product_added=Min("storeproduct__created_at"),
)
```

## When You _Want_ Inactive Records

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
2. Add a runtime check (e.g. SQL regex) to catch annotations and other bypass cases.
3. Use `all_objects` and `disable_active_filter_query_check()` when you intentionally need inactive records.

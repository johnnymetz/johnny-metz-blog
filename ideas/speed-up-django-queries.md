# Speed up Django queries

```
- Multiple prefetches levels: .prefetch_related("field1__field2__field3")
- Use Python to prevent a new query
	- List comprehension over .values_lists(), filter() or exclude()
  - In a loop, use qs[0] over qs.first()
- Use zen_queries and query_count() decorator
- Don't create large Q objects
- select related or prefetch related for joint prefetches:
  - prefetch_related: "object__objects"
  - not sure: "objects__object"
```

https://docs.djangoproject.com/en/4.0/ref/models/querysets/#prefetch-related

For the most part

- Use select_related() and prefetch_related()
  - Use `prefetch_related("field1__field2__field3")`

## Do as much work in the database as possible

```
with ExitStack() as stack:
    stack.enter_context(disable_all_validation())
    stack.enter_context(timer())

    products = fetch(Product.objects.order_by("pk").select_related("contract"))

    stack.enter_context(queries_disabled())

    lst = []
    for p in products:
        lst.append({"code": p.code, "contract__kind": p.contract.kind if p.contract else None})

with ExitStack() as stack:
    stack.enter_context(disable_all_validation())
    stack.enter_context(timer())

    qs = Product.objects.order_by("pk").values("code", "contract__kind")

print(lst == list(qs))
```

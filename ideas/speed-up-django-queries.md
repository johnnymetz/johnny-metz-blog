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

## select_related + prefetch_related

Note about how Django handles select_related and prefetch_related together:

select_related on its own does NOT make an extra DB query.
prefetch_related on its own makes a new DB query for every field, e.g. prefetch_related("field1**field2**field3\_\_field4") will prefetch fields 1, 2, 3 and 4 which totals 4 extra DB queries.
select_related takes precedence over prefetch_related so our query above only makes 1 extra DB hit. Without the .select_related("user") it would be 2.

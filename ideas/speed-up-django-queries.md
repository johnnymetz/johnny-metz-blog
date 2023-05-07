# Speed up Django queries

Write a blog post in markdown with a title about tips and tricks for optimizing Django query performance that are not listed in https://docs.djangoproject.com/en/4.2/topics/db/optimization/. The post should discuss:

- Use `assertNumQueries` in tests to ensure your code is making the expected number of queries. If you're using pytest-django, which I recommend, use `django_assert_num_queries`.
- Use https://github.com/jmcarp/nplusone to catch N+1 queries. This is a great backstop and have caught tons of N+1 queries. Note the package is orphaned and doesn't catch all N+1 violations. For example, I've noticed it doesn't work with `.only()` or `.defer()`. For example, the following is an N+1 query but nplusone doesn't catch it:
- Use https://github.com/dabapps/django-zen-queries to gain control over which parts of your code are allowed to run queries, and which aren't. I commonly use this after prefetching objects to ensure I've prefetched everything I need.
- Use Python to prevent a new query on prefetched objects. For example, use a list complehension instead of .values_lists(), filter() or exclude(). Another example, use qs[0] instead of qs.first()
- Use `defer()` to prevent fetching large unused fields, such as `JSONField` and `TextField`. Loading these fields into a Django object can consume a lot of memory and be very slow.

## Old

```
- Use nplusone package
- Use zen_queries and query_count() decorator
- Use `assertNumQueries` and `django_assert_num_queries` in tests
- Use Python to prevent a new query
	- List comprehension over .values_lists(), filter() or exclude()
  - In a loop, use qs[0] over qs.first()
- Don't create large Q objects
- Multiple prefetches levels: .prefetch_related("field1__field2__field3")
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

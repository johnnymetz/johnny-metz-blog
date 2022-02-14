# Post Ideas

- Anonymous volumes in docker and why you should use them
  - [SO](https://stackoverflow.com/questions/46166304/docker-compose-volumes-without-colon)
  - [Blog](https://towardsdatascience.com/the-complete-guide-to-docker-volumes-1a06051d2cce)
- docker system prune -a -f --volumes
- Don't use first() with prefetch()
- Hit host from docker container
- Prevent push directly to main branch on GitHub
- git merge vs git merge --squash vs git rebase
- git log -S
- DRF serializer field for date field object
- Dataclass vs namedtuple vs class
- Python mocking, import from where it’s called not defined
- Rate limiting in Django and DRF
- Docker + Django + React (docker-compose) and Makefile

Prefetch blog:

```
- Multiple levels prefetches all levels: .prefetch_related("field1__field2__field3")
- Use Python to prevent a new query
	- List comprehension over .values_lists(), filter() or exclude()
- Use zen_queries
- Don't create large Q objects
- select related or prefetch related for joint prefetches:
  - prefetch_related: "object__objects"
  - not sure: "objects__object"
```

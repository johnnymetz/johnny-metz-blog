# Post Ideas

- Ways to check for Django membership

```
.annotate(member_count=Count("members")).filter(member_count__gt=0)
.filter(members__isnull=False)
Exists subquery
```

- git merge vs git merge --squash vs git rebase
- Run cypress tests in docker
- Dataclass vs namedtuple vs class
- Use watchman for django in docker
- Rate limiting in Django and DRF
- Docker + Django + React (docker-compose)
- DRF serializer field for date field object
- DRF api design passing choices to frontend
- DRY Formik fields
- Python mocking, import from where it’s called not defined
- git log -S

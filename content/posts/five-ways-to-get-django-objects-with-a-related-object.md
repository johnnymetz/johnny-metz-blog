---
title: '5 ways to get all Django objects with a related object'
date: 2021-10-01T13:08:48-07:00
tags:
  - Python
  - Django
ShowToc: true
---

In Django, a [related object](https://docs.djangoproject.com/en/3.2/ref/models/relations/) is a model instance used in the one-to-many or many-to-many context.

For example, let's look at the built-in `User` model, which has a many-to-many relationship with the `Group` model.

```python
class User(models.Model):
    groups = models.ManyToManyField(Group, related_name="groups")
```

For any given `User` object, all linked `Group` objects are called "related objects". Here are 5 ways to fetch all `User` objects with at least one related `Group` object.

## Iterate over each object in Python

```python
users = []
for user in User.objects.prefetch_related("groups"):
    if user.groups.exists():
        users.append(user)
```

Probably the most popular approach but there are two problems:

- Doesn't return a queryset so we can't do any more work in the database, which isn't [ideal for performance](https://docs.djangoproject.com/en/3.2/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Makes a total of two database queries because [prefetch_related does a separate lookup for each relationship](https://docs.djangoproject.com/en/dev/ref/models/querysets/#prefetch-related).

Let's see some other query count examples with `prefetch_related`:

```python
User.objects.all()                                           # 1 query
User.objects.prefetch_related("groups")                      # 2 queries
User.objects.prefetch_related("groups__permissions")         # 3 queries
User.objects.prefetch_related("groups", "user_permissions")  # 3 queries
```

All other methods in this list make only one database query.

## isnull field lookup and distinct()

```python
users = User.objects.filter(groups__isnull=False).distinct()
```

Be sure to remember to use `distinct()`. Without it, each `User` is duplicated `n` times, where `n` is the number of groups the user belongs to. Definitely a little hacky. I wouldn't recommend using it in practice but it's an interesting approach to understand.

## queryset.annotate() and Count()

```python
from django.db.models import Count

users = (
    User.objects
    .annotate(group_count=Count("groups"))
    .filter(group_count__gt=0)
)
```

Readable and makes a single database query. The only con is it's slightly slower than the next two solutions because it counts all groups instead of stopping at the first one.

## queryset.annotate() and Exists() subquery

```python
from django.db.models import Exists, OuterRef

users = (
    User.objects
    .annotate(has_group=Exists(Group.objects.filter(user=OuterRef("pk"))))
    .filter(has_group=True)
)
```

Very fast. `Exists()` will stop once a single record is found. Per the [Django documentation](https://docs.djangoproject.com/en/3.2/ref/models/expressions/#exists-subqueries):

> Exists is a Subquery subclass that uses an SQL EXISTS statement. In many cases it will perform better than a subquery since the database is able to stop evaluation of the subquery when a first matching row is found.

## Exists() subquery

```python
users = (
    User.objects
    .filter(Exists(Group.objects.filter(user=OuterRef("pk"))))
)
```

Same solution as above but slightly better if we don't want to return the `has_group` field. This is called the [conditional filter](https://docs.djangoproject.com/en/3.2/ref/models/conditional-expressions/#conditional-filter):

> When a conditional expression returns a boolean value, it is possible to use it directly in filters. This means that it will not be added to the SELECT columns, but you can still use it to filter results

**Which of these solutions do you prefer?**

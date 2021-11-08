---
title: '5 ways to get all Django objects with a related object'
date: 2021-10-01T13:08:48-07:00
description: 'Five ways to query for all Django objects with a relationship to a different Django object'
tags:
  - Python
  - Django
ShowToc: true
draft: true
---

In Django, a [related object](https://docs.djangoproject.com/en/3.2/ref/models/relations/) is a model instance used in the one-to-many or many-to-many context.

Let's look at the built-in `User` and `Group` objects, which have a many-to-many relationship.

```python
class User(models.Model):
    groups = models.ManyToManyField(Group, related_name="groups")
```

Here are 5 ways to fetch all `User` objects with at least one related `Group` object.

## Iterate over each object in Python

```python
users = []
for user in User.objects.prefetch_related("groups"):
    if user.groups.exists():
        users.append(user)
```

This is probably the most popular approach but there are two problems:

- Makes a total of two database queries. All others in this list make only one.
- Doesn't return a queryset so we can't do any more work in the database, which isn't [ideal for performance](https://docs.djangoproject.com/en/3.2/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).

## isnull field lookup and distinct()

```python
users = User.objects.filter(groups__isnull=False).distinct()
```

Be sure to remember to use `distinct()`. Without it, each `User` is duplicated `n` times, where `n` is the number of groups the user belongs to. This is a little hacky. I wouldn't recommend using it in practice but it's an interesting approach to understand.

## queryset.annotate() and Count()

```python
users = (
    User.objects
    .annotate(group_count=Count("groups"))
    .filter(group_count__gt=0)
)
```

This a fast and readable solution. It only makes one database query. However, this is slower than the next two solutions because it counts all groups instead of stopping at the first one.

## queryset.annotate() and Exists()

```python
users = (
    User.objects
    .annotate(has_group=Exists(Group.objects.filter(user=OuterRef("pk"))))
    .filter(has_group=True)
)
```

This a fast and readable solution. `Exists` will stop once a single record is found. Per the [Django documentation](https://docs.djangoproject.com/en/3.2/ref/models/expressions/#exists-subqueries):

> Exists is a Subquery subclass that uses an SQL EXISTS statement. In many cases it will perform better than a subquery since the database is able to stop evaluation of the subquery when a first matching row is found.

## Exists()

```python
users = (
    User.objects
    .filter(Exists(Group.objects.filter(user=OuterRef("pk"))))
)
```

The same solution as above but slightly better if we don't want to return the `has_group` field. This is called the [conditional filter](https://docs.djangoproject.com/en/3.2/ref/models/conditional-expressions/#conditional-filter):

> When a conditional expression returns a boolean value, it is possible to use it directly in filters. This means that it will not be added to the SELECT columns, but you can still use it to filter results

May your Django code be readable and performant.

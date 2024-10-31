---
title: '5 Ways to Get the Latest Record Per Group in Django'
date: 2024-10-30T19:04:39-07:00
tags:
  - Python
  - Django
ShowToc: true
draft: true
---

When working with Django models, it's common to need the latest record for each group in a queryset. This can be tricky, especially when dealing with large datasets. In this blog post, we'll explore five different approaches to achieve this, using the following `Todo` model as our example:

```python
class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
```

## Approach 1: Python Max with Prefetch

```python
[
    max(user.todo_set.all(), key=lambda x: x.updated_at, default=None)
    for user in User.objects.prefetch_related("todo_set")
]
```

- Performs heavy computation in Python rather than leveraging the database, which is [bad for performance](https://docs.djangoproject.com/en/5.1/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Makes two database queries: one for users and one for todos.

## Approach 2: Prefetch with Ordered QuerySet

```python
from django.db.models import Prefetch

[
    user.todo_set.first()
    for user in User.objects.prefetch_related(
        Prefetch("todo_set", queryset=Todo.objects.order_by("-updated_at")),
    )
]
```

- Similar to the first approach but computes the max in the database, which is slightly more efficient.

## Approach 3: Annotate with Max and Filter

```python
from django.db.models import F, Max

Todo.objects.annotate(
    latest_updated_at=Max("user__todo__updated_at")
).filter(updated_at=F("latest_updated_at"))
```

- Performs the

## Approach 4: Subquery with OuterRef

```python
from django.db.models import OuterRef, Subquery

User.objects.annotate(
    latest_todo_id=Subquery(
        Todo.objects.filter(user=OuterRef("id"))
        .order_by("-updated_at")
        .values("id")[:1]
    )
)
```

- Efficient and scalable; performs the computation in the database.
- Only returns the latest `Todo` id, not the entire `Todo` object.

## Approach 5: Distinct with Order By

```python
Todo.objects.order_by("user", "-updated_at").distinct("user")
```

- Leverages PostgreSQL's DISTINCT ON feature to get the latest todo per user.
- Orders todos by user and -updated_at, then selects the first unique user.
- Best approach but limited to PostgreSQL.

Now, let's extend our `Todo` model to include `priority` and `is_done` fields:

```python
class Todo(models.Model):
    class Priority(models.IntegerChoices):
        HIGH = 1, "High"
        MEDIUM = 2, "Medium"
        LOW = 3, "Low"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    priority = models.PositiveSmallIntegerField(choices=Priority)
    is_done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
```

Suppose we want to fetch the latest undone todo per user and priority group. Here's how we can achieve that:

```python
Todo.objects.filter(is_done=False)
    .order_by("user", "priority", "-updated_at")
    .distinct("user", "priority")
```

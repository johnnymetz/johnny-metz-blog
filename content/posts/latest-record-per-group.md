---
title: '5 Ways to Get the Latest Record Per Group in Django'
date: 2024-11-14T12:00:00-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/books-stacked.png'
---

In a Django application, querying the latest record for each group is a common requirement. This can be tricky, especially when dealing with large datasets. In this blog post, we'll explore five different solutions to retrieve the latest task per user (ranked from worse to best in terms of performance and readability) given the following `Task` model:

```python
class Task(models.Model):
    class Priority(models.IntegerChoices):
        HIGH = 1, "High"
        MEDIUM = 2, "Medium"
        LOW = 3, "Low"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    priority = models.PositiveSmallIntegerField(choices=Priority)
    is_complete = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
```

## Solution 1: Python Max with Prefetch

```python
latest_tasks = [
    max(user.task_set.all(), key=lambda x: x.updated_at, default=None)
    for user in User.objects.prefetch_related("task_set")
]
```

Performs heavy computation in Python rather than leveraging the database, which is [bad for performance](https://docs.djangoproject.com/en/5.1/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python). Also makes two database queries (better solutions do it in one).

## Solution 2: Prefetch with Ordered QuerySet

```python
from django.db.models import Prefetch

latest_tasks = [
    user.task_set.first()
    for user in User.objects.prefetch_related(
        Prefetch("task_set", queryset=Task.objects.order_by("-updated_at")),
    )
]
```

Similar to the first solution but computes the max in the database, which is slightly more efficient.

## Solution 3: Subquery with OuterRef

```python
from django.db.models import OuterRef, Subquery

users_with_latest_task = User.objects.annotate(
    latest_task_id=Subquery(
        Task.objects.filter(user=OuterRef("id"))
        .order_by("-updated_at")
        .values("id")[:1]
    )
)
```

Fetches the latest task per user in a single query. But only returns the task ID, so we'd need to make another query to get the full task object if needed.

## Solution 4: Annotate with Max and Filter

```python
from django.db.models import F, Max

latest_tasks = (
    Task.objects
    .alias(latest_updated_at=Max("user__task__updated_at"))
    .filter(updated_at=F("latest_updated_at"))
)
```

The least intuitive approach. Issues a `GROUP BY ... HAVING ...` query under the hood. Note we're using [`alias`](https://docs.djangoproject.com/en/5.1/ref/models/querysets/#alias) instead of [`annotate`](https://docs.djangoproject.com/en/5.1/ref/models/querysets/#annotate) because we don't need the `latest_updated_at` field in the result.

## Solution 5: Postgres DISTINCT ON

```python
latest_tasks = Task.objects.order_by("user", "-updated_at").distinct("user")
```

The best / most concise approach but only available in Postgres. Leverages its [DISTINCT ON](https://neon.tech/postgresql/postgresql-tutorial/postgresql-distinct-on) clause to get the latest task per user in a single query.

To show how elegant this solution is, let's say we want to fetch the latest uncompleted task per user and priority group:

```python
latest_tasks = (
    Task.objects.filter(is_complete=False)
    .order_by("user", "priority", "-updated_at")
    .distinct("user", "priority")
)
```

May your Django queries be fast and clean.

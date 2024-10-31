# Fetch latest objects / values in Django

## Titles

- 5 ways to get the latest record per group in Django

## Notes

Fetch latest object in a queryset:

- Use `latest('field_name')`
- Use `latest()` with `Model.get_latest_by = 'field_name'`
- Use `order_by('-field_name').first()`
- Use `order_by('-field_name')[0]`

Fetch the latest object per group in a queryset:

- Use a subquery

```
latest_browser_client_subquery = (
    models.BrowserClient.objects.filter(user=OuterRef("user"))
    .order_by("-updated_at")
    .values("id")[:1]
)

campaign_users = (
    campaign.users.select_related("user")
    .annotate(latest_browser_client_id=Subquery(latest_browser_client_subquery))
    .order_by("email")
)
```

- In Postgres, use `DISTINCT ON` with `order_by`

```
latest_browser_clients = (
    qs
    .order_by("user", "-updated_at")
    .distinct("user")
)
```

[SQL Query Optimization for Large IN Queries](https://medium.com/@mukul.chaware13/sql-query-optimization-for-large-in-queries-74f58dc524b6)

## ChatGPT Prompts

### Initial Draft

[ChatGPT Link](https://chatgpt.com/c/6722e3c0-f494-8000-aa17-f999874e459e)

Write a blog post titled "5 ways to get the latest record per group in Django".

Here is the Todo model we're using an example:

```python
class Todo(models.Model):
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    updated_at = models.DateTimeField(auto_now=True)
```

Approach 1:

```python
[
    max(user.todo_set.all(), key=lambda x: x.updated_at, default=None)
    for user in User.objects.prefetch_related("todo_set")
]
```

- Does a lot of work in Python, instead of the database, which isn't [ideal for performance](https://docs.djangoproject.com/en/5.1/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Makes a total of two database queries. Other approaches can do it in one.

Approach 2:

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

Approach 3:

```python
from django.db.models import F, Max

Todo.objects.annotate(
    latest_updated_at=Max("user__todo__updated_at")
).filter(updated_at=F("latest_updated_at"))
```

Approach 4:

```python
from django.db.models import OuterRef, Subquery

latest_todos_subquery = Todo.objects.filter(user=OuterRef("id")).order_by(
    "-updated_at"
)
users = User.objects.annotate(
  latest_todo_id=Subquery(latest_todos_subquery.values("id")[:1])
)
```

Approach 5:

```python
Todo.objects.order_by("user", "-updated_at").distinct("user")
```

- Only available in Postgres
- Best approach

Come up with concise labels and some brief notes for each approach.

Now let's say we extend our Todo model to include `priority` and `is_done` fields:

```python
class Todo(models.Model):
    class Priority(models.IntegerChoices):
        HIGH = 1, "High"
        MEDIUM = 2, "Medium"
        LOW = 3, "Low"

    user = models.ForeignKey(User, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    priority = models.PositiveSmallIntegerField(choices=Priority, db_index=True)
    is_done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
```

And we want to fetch the latest undone todo per user and priority group.

Solution:

```python
Todo.objects.filter(is_done=False)
.order_by("user", "priority", "-updated_at")
.distinct("user", "priority")
```

### Discover

Let's say I have the following Django models:

```
class User: base Django User class

class Todo:
    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    updated_at = models.DateTimeField(auto_now=True)
```

I want to fetch the latest todo per user.

I know I can do so in Postgres using the following query:

```
Todo.objects.order_by("user", "-updated_at").distinct("user")
```

Give me 3 other ways to do this.

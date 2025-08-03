---
title: 'The Django db_default Gotcha That Breaks Your Code'
date: 2025-08-03T13:46:58-07:00
tags:
  - Python
  - Django
ShowToc: true
cover:
  image: 'covers/django.png'
---

Starting in Django 5.0, you can use [`db_default`](https://docs.djangoproject.com/en/5.2/ref/models/fields/#db-default) to define database-level default values for model fields. It's a great feature but comes with a subtle and dangerous gotcha that can silently break your code before the object is ever saved.

## The Gotcha in Action

Let's say you're building a simple task manager, and you want to track whether a task is completed:

```python
from django.db import models

class Task(models.Model):
    is_completed = models.BooleanField(db_default=False)
```

The `db_default` option ensures the database applies the default in raw `INSERT` queries and [prevents errors during a rolling deployment]({{< relref "posts/multistep-database-changes.md" >}}#backward-compatible).

Now consider this perfectly normal code:

```python
task = Task()
if task.is_completed:
    print("Task is done!")
else:
    print("Task is not done yet")
```

You'd expect this to print `"Task is not done yet"` but it prints `Task is done!`.

Let's inspect the value:

```python
print(task.is_completed)
# <django.db.models.expressions.DatabaseDefault object ...>
```

Even though we set `db_default=False`, this isn't `False` — it's a special wrapper object.

## Why This Happens

The [Django docs](https://docs.djangoproject.com/en/5.2/ref/models/fields/#db-default) explain this behavior:

> If a field has a `db_default` without a `default` set and no value is assigned to the field, a `DatabaseDefault` object is returned as the field value on unsaved model instances. The actual value for the field is determined by the database when the model instance is saved.

In short: The field doesn't hold the actual default value until the instance is saved.

```python
task = Task()
task.save()
print(task.is_completed)
# False
```

This issue isn't limited to booleans. It can show up with any field where you use `db_default`:

- `CharField(db_default="")`
- `IntegerField(db_default=0)`
- `JSONField(db_default={})`
- `DurationField(db_default=timedelta())`

Accessing the field before saving can trigger errors — or worse, silently break your logic.

## How to Fix It

Fortunately, the fix is simple — and straight from the [Django docs](https://docs.djangoproject.com/en/5.2/ref/models/fields/#db-default):

> If both `db_default` and `Field.default` are set, `default` will take precedence when creating instances in Python code. `db_default` will still be set at the database level and will be used when inserting rows outside of the ORM or when adding a new field in a migration.

So you should define the field like this:

```python
is_completed = models.BooleanField(default=False, db_default=False)
```

This approach covers all the bases. Here's how `default` and `db_default` compare:

| Behavior                        | `default` | `db_default` |
| ------------------------------- | --------- | ------------ |
| Applies default in Python code  | ✅        | ❌           |
| Applies default in the database | ❌        | ✅           |
| Safe for rolling deployments    | ❌        | ✅           |

When you need consistent behavior across the stack, use both `default` and `db_default`.

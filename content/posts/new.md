---
title: 'How to sort a Django QuerySet with a custom order'
date: 2022-07-03T12:48:49-07:00
tags:
  - Python
  - Django
ShowToc: true
draft: true
---

I occasionally need to sort my Django objects with a custom order.

For example, let's take a simple `Todo` model:

```python
class Todo(models.Model):
    class Priority(models.TextChoices):
        HIGH = "HIGH", _("High")
        MEDIUM = "MEDIUM", _("Medium")
        LOW = "LOW", _("Low")

    title = models.CharField(max_length=255)
    priority = models.CharField(max_length=10, choices=Priority.choices, db_index=True)
    done = models.BooleanField(default=False)
```

And a list of todos:

<!-- TODO: try adding checkbox to done items -->

| Id  | Title                  | Priority | Done |
| --- | ---------------------- | -------- | ---- |
| 1   | Add linters            | Medium   | Yes  |
| 2   | Fix bug                | High     | No   |
| 3   | Increase test coverage | Medium   | No   |
| 4   | Refactor views         | Low      | No   |
| 5   | Run tests in CI        | High     | Yes  |

Our goal is to order these items from high to low priority. And then by title to keep the results consistent for priority levels with multiple items. Our expected result should be the id's in the following order: `[2, 5, 1, 3, 4]`

There are several ways to do this. Let's review them and when to use some methods over others.

## Sort in Python using `sorted`

```python
PREFERENCE = {
    Todo.Priority.HIGH: 1,
    Todo.Priority.MEDIUM: 2,
    Todo.Priority.LOW: 3,
}
sorted(
    Todo.objects.all(),
    key=lambda x: [PREFERENCE[x.priority], x.title],
)
```

Definitely the most common approach I see in the wild but there are two big problems:

- Does the sorting in Python, instead of in the database, which is [bad for performance](https://docs.djangoproject.com/en/3.2/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Returns a list, instead of a queryset, so we can’t do any more work in the database, which is also bad for performance.

## Sort in Database using Conditional Expressions

[Conditional expressions](https://docs.djangoproject.com/en/4.0/ref/models/conditional-expressions/) allow you to implement conditional logic into your database queries.

```python
custom_order = Case(
    When(priority=Todo.Priority.HIGH, then=Value(1)),
    When(priority=Todo.Priority.MEDIUM, then=Value(2)),
    When(priority=Todo.Priority.LOW, then=Value(3)),
)
Todo.objects.annotate(custom_order=custom_order).order_by(
    "custom_order", "title"
)
```

This

<!-- Sort in Python using sorted function-->
<!-- Sort in Database using IntegerChoices -->

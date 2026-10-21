---
title: 'Sort a Django Queryset by a Custom Order'
date: 2023-01-02T17:00:00-08:00
tags:
  - Python
  - Django
  - Query Optimization
ShowToc: true
cover:
  image: 'covers/django-sorting.png'
---

Sorting a Django queryset by a custom order is trickier than it looks, and choosing the wrong solution for your use case can cripple your application's performance.

For example, let’s take a simple `Todo` model:

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

| Id  | Title                  | Priority | Done |
| --- | ---------------------- | -------- | ---- |
| 1   | Add linters            | Medium   | Yes  |
| 2   | Fix bug                | High     | No   |
| 3   | Increase test coverage | Medium   | No   |
| 4   | Refactor views         | Low      | No   |
| 5   | Run tests in CI        | High     | Yes  |

Our query set goal is to order these items from high to low `priority`. For priority levels with multiple items, we'll also order by `title` to keep the results consistent. The expected result should be the id’s in the following order: `[2, 5, 1, 3, 4]`

Let’s review some strategies for performing this sort. Then we’ll benchmark each one and discuss when to use them.

## Sort in Python using `sorted`

```python
PRIORITY_ORDER = {
    Todo.Priority.HIGH: 1,
    Todo.Priority.MEDIUM: 2,
    Todo.Priority.LOW: 3,
}
sorted(
    Todo.objects.all(),
    key=lambda x: [PRIORITY_ORDER[x.priority], x.title],
)
```

Definitely the most common approach I see in the wild but there are two big problems, which make this the slowest solution for large datasets:

- Executes the sort in Python, instead of in the database, which is [bad for performance](https://docs.djangoproject.com/en/3.2/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Returns a list, instead of a queryset, so you can’t do any more work in the database, which is also bad for performance.

## Sort in Database using a Conditional Expression

[Conditional expressions](https://docs.djangoproject.com/en/4.0/ref/models/conditional-expressions/) let you to implement conditional logic into your database queries. This solution is faster than sorting in Python because the sort is done directly in the database.

```python
from django.db.models import Case, Value, When

priority_order = Case(
    When(priority=Todo.Priority.HIGH, then=Value(1)),
    When(priority=Todo.Priority.MEDIUM, then=Value(2)),
    When(priority=Todo.Priority.LOW, then=Value(3)),
)
Todo.objects.alias(priority_order=priority_order).order_by("priority_order", "title")
```

Note, `alias()` is the same as `annotate()` but doesn’t return the `priority_order` field in the result (see [docs](https://docs.djangoproject.com/en/4.0/ref/models/querysets/#alias)).

The solution is quite verbose so I generally like to throw this into a [custom model manager](https://docs.djangoproject.com/en/4.0/topics/db/managers/#custom-managers).

```python
class TodoQuerySet(models.QuerySet):
    def order_by_priority(self):
        return self.alias(priority_order=Case(...)).order_by("priority_order", "title")

class Todo(models.Model):
    ...
    objects = TodoQuerySet.as_manager()
```

This allows us to write compact and easy to read queries:

```python
# Sort all todos
Todo.objects.order_by_priority()

# Get the highest priority uncompleted todo
Todo.objects.filter(done=False).order_by_priority().first()

# Get the highest 5 priority uncompleted todos
Todo.objects.filter(done=False).order_by_priority()[:5]

# Sort all high and medium priority todos
Todo.objects.exclude(priority=Todo.Priority.LOW).order_by_priority()
```

Database indexes will improve performance even further. The indexes you choose are dependent on your query workload. The index below will optimize the `Todo.objects.order_by_priority()` query. Note, we need to extract the `Priority` class out of the model, otherwise Python will raise a `'Priority' is not defined` exception.

```python
class Priority(models.IntegerChoices):
    HIGH = 1, _("High")
    MEDIUM = 2, _("Medium")
    LOW = 3, _("Low")

class Todo(models.Model):
    ...
    class Meta:
        indexes = [
            models.Index(
                Case(
                    When(priority=Priority.HIGH, then=Value(1)),
                    When(priority=Priority.MEDIUM, then=Value(2)),
                    When(priority=Priority.LOW, then=Value(3)),
                ),
                "title",
                name="priority_order_title_idx",
            ),
        ]
```

Conditional expressions are powerful and can be used in queries with very advanced logic. See the [docs](https://docs.djangoproject.com/en/4.0/ref/models/conditional-expressions/) for more examples.

## Sort in Database using `IntegerChoices`

Django lets you represent choices as integers in a database using the `IntegerChoices` class (see [Enumeration Types](https://docs.djangoproject.com/en/4.0/ref/models/fields/#enumeration-types)). Refactor the `priority` field like so:

```python
class Todo(models.Model):
    ...
    class Priority(models.IntegerChoices):
        HIGH = 1, _("High")
        MEDIUM = 2, _("Medium")
        LOW = 3, _("Low")

    priority = models.PositiveSmallIntegerField(choices=Priority.choices, db_index=True)
```

This allows us to perform our sort in the database without the need of conditional expressions:

```python
Todo.objects.order_by("priority", "title")
```

Similar to the last solution, an index can significantly improve performance:

```python
class Todo(models.Model):
    ...
    class Meta:
        indexes = [
            models.Index(fields=["priority", "title"]),
        ]
```

This is the fastest and most straightforward solution but has some downfalls:

- Requires you to perform a database migration if the order ever changes.
- Represents strings as integers in the database, which can be confusing.
- Doesn’t work for complex sorting logic, e.g. order records from high to low `priority` but move any item with "urgent" in the title to the top of the list.

## Benchmarks

I took the following benchmarks (in seconds) using Python 3.11.1, Django 4.1 and PostgreSQL 15.1.

| Record count | IntegerChoices w/ index | Conditional Expression w/ index | IntegerChoices w/o index | Conditional Expression w/o index | Python sort |
| ------------ | ----------------------- | ------------------------------- | ------------------------ | -------------------------------- | ----------- |
| 100,000      | 0.7                     | 0.8                             | 1.0                      | 1.0                              | 1.0         |
| 1,000,000    | 7.4                     | 8.3                             | 9.2                      | 9.8                              | 10.6        |
| 5,000,000    | 41                      | 48                              | 57                       | 87                               | 114         |
| 10,000,000   | 91                      | 95                              | 204                      | 252                              | 404         |

As you can see, any strategy is fine for small datasets. For large datasets, sorting in the database using `IntegerChoices` is best. Conditional expressions are a good alternative if the sorting logic is complex. Always create an index when sorting large tables in the database.

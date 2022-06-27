---
title: 'Sort a Django queryset with a custom order'
date: 2022-07-03T12:48:49-07:00
tags:
  - Python
  - Django
ShowToc: true
draft: true
---

I occasionally need to sort a Django queryset with a custom order.

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

Our goal is to order these items from high to low `priority`. For priority levels with multiple items, we'll also order by `title` to keep the results consistent. Our expected result should be the id's in the following order: `[2, 5, 1, 3, 4]`

Let's review some strategies for performing this sort. Then we'll benchmark each strategy and discuss when to use them.

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

Definitely the most common approach I see in the wild but there are two big problems, which make this the slowest solution:

- Performs the sort in Python, instead of in the database, which is [bad for performance](https://docs.djangoproject.com/en/3.2/topics/db/optimization/#do-database-work-in-the-database-rather-than-in-python).
- Returns a list, instead of a queryset, so we can’t do any more work in the database, which is also bad for performance.

## Sort in Database using a Conditional Expression

[Conditional expressions](https://docs.djangoproject.com/en/4.0/ref/models/conditional-expressions/) let you to implement conditional logic into your database queries. This solution is faster than sorting in Python because the sort is done directly in the database.

```python
from django.db.models import Case, Value, When

preference = Case(
    When(priority=Todo.Priority.HIGH, then=Value(1)),
    When(priority=Todo.Priority.MEDIUM, then=Value(2)),
    When(priority=Todo.Priority.LOW, then=Value(3)),
)
Todo.objects.alias(preference=preference).order_by("preference", "title")
```

Note, `alias()` is the same as `annotate()` but doesn't return the `preference` field in the result (see [docs](https://docs.djangoproject.com/en/4.0/ref/models/querysets/#alias)).

The solution is quite verbose so I generally like to throw this into a [custom model manager](https://docs.djangoproject.com/en/4.0/topics/db/managers/#custom-managers).

```python
class TodoQuerySet(models.QuerySet):
    def order_by_priority(self):
        from customsort.models import Todo

        preference = Case(...)
        return self.alias(preference=preference).order_by("preference", "title")

class Todo(models.Model):
    ...
    objects = TodoQuerySet.as_manager()
```

This allows us to write compact and easy to read queries:

```python
# sort all todos
Todo.objects.order_by_priority()

# sort all uncompleted todos
Todo.objects.filter(done=False).order_by_priority()

# sort all high and medium priority todos
Todo.objects.exclude(priority=Todo.Priority.LOW).order_by_priority()
```

Conditional expressions are powerful and can be used in queries with very advanced logic. See the [docs](https://docs.djangoproject.com/en/4.0/ref/models/conditional-expressions/) for more examples.

## Sort in Database using `IntegerChoices`

Django lets you represent choices as integers in a database using the `IntegerChoices` class (see [Enumeration Types](https://docs.djangoproject.com/en/4.0/ref/models/fields/#enumeration-types)). So we can refactor the `priority` field like so:

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

This is the fastest and most straightforward solution but has some downfalls:

- Requires you to perform a database migration if the order ever changes.
- Representing strings with integers in a database can be confusing and hard to digest.
- Doesn't work for complex sorting logic.

## Benchmarks

I took the following benchmarks on my 16GB RAM MacBook Pro.

| Record count | IntegerChoices | Conditional Expression | Python sort |
| ------------ | -------------- | ---------------------- | ----------- |
| 100,000      | 1.0s           | 1.0s                   | 1.0s        |
| 1,000,000    | 9.2s           | 9.8s                   | 10.6s       |
| 5,000,000    | 57s            | 87s                    | 114s        |
| 10,000,000   | 204s           | 252s                   | 404s        |

As we can see, any strategy is fine for small datasets. For large datasets, sorting in the database using `IntegerChoices` is best. Conditional expressions are a good alternative if the sorting logic is overly complex.

---
title: 'How to sort a Django QuerySet with a custom order'
date: 2022-07-03T12:48:49-07:00
tags:
  - Python
  - Django
draft: true
---

I occasionally need to sort my Django objects with a custom order.

For example, let's take the following `Todo` model:

```python
class Todo(models.Model):
    class Priority(models.TextChoices):
        HIGH = "HIGH", _("High")
        MEDIUM = "MEDIUM", _("Medium")
        LOW = "LOW", _("Low")

    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=Priority.choices, db_index=True)
```

<!-- Sort in Python using sorted function-->
<!-- Sort in Database using IntegerChoices -->
<!-- Sort in Database using Conditional Expressions -->

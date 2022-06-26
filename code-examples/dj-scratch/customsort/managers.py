from django.db import models
from django.db.models import Case, Value, When


class TodoQuerySet(models.QuerySet):
    def order_by_priority(self):
        from customsort.models import Todo

        new_priority = Case(
            When(priority=Todo.Priority.HIGH, then=Value(1)),
            When(priority=Todo.Priority.MEDIUM, then=Value(2)),
            When(priority=Todo.Priority.LOW, then=Value(3)),
        )
        # Sort by id also just so it's consistent if there's a tie
        return self.annotate(new_priority=new_priority).order_by("new_priority", "id")


class TodoManager(models.Manager):
    def get_queryset(self):
        return TodoQuerySet(self.model, using=self._db)

    def order_by_priority(self):
        return self.get_queryset().order_by_priority()

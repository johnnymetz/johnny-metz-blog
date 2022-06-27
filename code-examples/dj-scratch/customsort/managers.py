from django.db import models
from django.db.models import Case, Value, When


class TodoQuerySet(models.QuerySet):
    def order_by_priority(self):
        from customsort.models import Todo

        preference = Case(
            When(priority=Todo.Priority.HIGH, then=Value(1)),
            When(priority=Todo.Priority.MEDIUM, then=Value(2)),
            When(priority=Todo.Priority.LOW, then=Value(3)),
        )
        return self.alias(preference=preference).order_by("preference", "title")

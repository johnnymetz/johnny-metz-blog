from django.db import models
from django.db.models import Case, Value, When
from django.utils.translation import gettext_lazy as _


class Priority(models.IntegerChoices):
    HIGH = 1, _("High")
    MEDIUM = 2, _("Medium")
    LOW = 3, _("Low")


PRIORITY_ORDER = Case(
    When(priority=Priority.HIGH, then=Value(1)),
    When(priority=Priority.MEDIUM, then=Value(2)),
    When(priority=Priority.LOW, then=Value(3)),
)


class TodoQuerySet(models.QuerySet):
    def order_by_priority(self):
        return self.alias(preference=PRIORITY_ORDER).order_by("preference", "title")


class Todo(models.Model):
    class Meta:
        indexes = [
            models.Index(fields=["priority", "title"], name="priority_title_idx"),
            models.Index(PRIORITY_ORDER, "title", name="priority_order_title_idx"),
        ]

    Priority = Priority

    objects = TodoQuerySet.as_manager()

    title = models.CharField(max_length=255)
    # priority = models.CharField(max_length=10, choices=Priority.choices, db_index=True)
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, db_index=True)
    done = models.BooleanField(default=False)

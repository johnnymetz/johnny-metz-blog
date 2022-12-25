from django.db import models
from django.utils.translation import gettext_lazy as _

from customsort.managers import TodoQuerySet


class Todo(models.Model):
    # class Priority(models.TextChoices):
    #     HIGH = "HIGH", _("High")
    #     MEDIUM = "MEDIUM", _("Medium")
    #     LOW = "LOW", _("Low")

    class Meta:
        indexes = [
            models.Index(fields=["priority", "title"]),
        ]

    class Priority(models.IntegerChoices):
        HIGH = 1, _("High")
        MEDIUM = 2, _("Medium")
        LOW = 3, _("Low")

    objects = TodoQuerySet.as_manager()

    title = models.CharField(max_length=255)
    # priority = models.CharField(max_length=10, choices=Priority.choices, db_index=True)
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, db_index=True)
    done = models.BooleanField(default=False)

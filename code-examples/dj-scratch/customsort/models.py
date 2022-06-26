from django.db import models
from django.utils.translation import gettext_lazy as _

from customsort.managers import TodoManager


class Todo(models.Model):
    class Priority(models.TextChoices):
        HIGH = "HIGH", _("High")
        MEDIUM = "MEDIUM", _("Medium")
        LOW = "LOW", _("Low")

    objects = TodoManager()

    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    priority = models.CharField(max_length=10, choices=Priority.choices, db_index=True)

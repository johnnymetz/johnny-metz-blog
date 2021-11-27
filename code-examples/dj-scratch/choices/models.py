from django.db import models


class Device(models.Model):
    class Size(models.TextChoices):
        SMALL = "S", "Small"
        MEDIUM = "M", "Medium"
        LARGE = "L", "Large"

    name = models.CharField(max_length=255)
    size = models.CharField(max_length=255, choices=Size.choices)

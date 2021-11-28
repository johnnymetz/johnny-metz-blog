from django.db import models


class Device(models.Model):
    class Size(models.TextChoices):
        SMALL = "S"
        MEDIUM = "M"
        LARGE = "L"

    name = models.CharField(max_length=255)
    size = models.CharField(max_length=255, choices=Size.choices)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

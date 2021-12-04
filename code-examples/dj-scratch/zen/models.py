from django.db import models


class Toolbox(models.Model):
    name = models.CharField(max_length=255)
    tools = models.ManyToManyField("Tool")

    def __str__(self) -> str:
        return f"{self.name}"


class Tool(models.Model):
    class Size(models.TextChoices):
        SMALL = "S"
        MEDIUM = "M"
        LARGE = "L"

    name = models.CharField(max_length=255)
    size = models.CharField(max_length=10, choices=Size.choices)

    def __str__(self) -> str:
        return f"{self.name}"

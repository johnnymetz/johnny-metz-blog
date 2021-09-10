from django.db import models


class Toolbox(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "version"],
                name="%(app_label)s_%(class)s_unique_name_version",
            )
        ]

    name = models.CharField(max_length=255)
    version = models.PositiveIntegerField()
    tools = models.ManyToManyField("Tool", related_name="toolboxes")

    def __str__(self) -> str:
        return f"{self.name}"


class Tool(models.Model):
    name = models.CharField(max_length=255)

    def __str__(self) -> str:
        return f"{self.name}"

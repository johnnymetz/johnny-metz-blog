from django.db import models


class Book(models.Model):
    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["name", "edition"],
                name="%(app_label)s_%(class)s_unique_name_edition",
            )
        ]

    name = models.CharField(max_length=255)
    edition = models.CharField(max_length=255)
    release_year = models.PositiveIntegerField(null=True)


# class Tool(models.Model):
#     class Meta:
#         constraints = [
#             models.UniqueConstraint(
#                 fields=["name", "version"],
#                 name="%(app_label)s_%(class)s_unique_name_version",
#             )
#         ]

#     name = models.CharField(max_length=255)
#     version = models.CharField(max_length=255)
#     created_on = models.DateTimeField(auto_now_add=True)


# class Movie(models.Model):
#     name = models.CharField(max_length=255)
#     year_released = models.PositiveIntegerField()
#     rating = models.PositiveIntegerField()

#     def __str__(self):
#         return self.name

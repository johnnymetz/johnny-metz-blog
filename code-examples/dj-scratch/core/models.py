from django.contrib.auth.models import User
from django.db import models
from django.utils.functional import cached_property


class Team(models.Model):
    name = models.CharField(max_length=255)
    users = models.ManyToManyField(User, through="TeamUser")

    @cached_property
    def total_points(self):
        return self.teamuser_set.aggregate(models.Sum("points"))["points__sum"] or 0


class TeamUser(models.Model):
    team = models.ForeignKey(Team, on_delete=models.CASCADE)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    points = models.IntegerField()


class Todo(models.Model):
    class Priority(models.IntegerChoices):
        HIGH = 1, "High"
        MEDIUM = 2, "Medium"
        LOW = 3, "Low"

    user = models.ForeignKey(User, null=True, blank=True, on_delete=models.CASCADE)
    title = models.CharField(max_length=255)
    done = models.BooleanField(default=False)
    priority = models.PositiveSmallIntegerField(choices=Priority.choices, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def save(self, *args, **kwargs):
        self.full_clean()
        return super().save(*args, **kwargs)

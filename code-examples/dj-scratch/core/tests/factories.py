from django.contrib.auth.models import User

import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from core.models import Team, Todo


class TeamFactory(DjangoModelFactory):
    class Meta:
        model = Team

    name = factory.Sequence(lambda n: f"Team {n}")


class TodoFactory(DjangoModelFactory):
    class Meta:
        model = Todo

    title = factory.Sequence(lambda n: f"Todo {n}")
    priority = FuzzyChoice(Todo.Priority)
    done = factory.Faker("pybool")


class UserFactory(factory.django.DjangoModelFactory):
    class Meta:
        model = User

    username = factory.Sequence(lambda n: f"user{n + 1}")
    email = factory.LazyAttribute(lambda obj: f"{obj.username}@test.com")

    @classmethod
    def _create(cls, model_class, *args, **kwargs):
        manager = cls._get_manager(model_class)
        # The default would use `manager.create(*args, **kwargs)`
        return manager.create_user(*args, **kwargs)

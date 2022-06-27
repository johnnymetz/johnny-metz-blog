import factory
from factory.django import DjangoModelFactory
from factory.fuzzy import FuzzyChoice

from customsort.models import Todo


class TodoFactory(DjangoModelFactory):
    class Meta:
        model = Todo

    title = factory.Sequence(lambda n: f"Todo {n}")
    priority = FuzzyChoice(Todo.Priority)

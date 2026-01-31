import factory
from factory.django import DjangoModelFactory

from core.models import Product, Store


class StoreFactory(DjangoModelFactory):
    class Meta:
        model = Store

    name = factory.Sequence(lambda n: f"Store {n}")


class ProductFactory(DjangoModelFactory):
    class Meta:
        model = Product

    name = factory.Sequence(lambda n: f"Product {n}")

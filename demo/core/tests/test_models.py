import pytest
from django.db.models import Count, Q
from django.test import TestCase

from core.active_filter_checks import (
    ActiveFilterMissingError,
    disable_active_filter_query_check,
)
from core.models import Product, Store, StoreProduct
from core.tests.factories import ProductFactory, StoreFactory


class TestModels(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.store2 = StoreFactory()

        self.product = ProductFactory()
        self.product2 = ProductFactory()

        self.x1 = StoreProduct.objects.create(
            store=self.store,
            product=self.product,
            active=True,
        )
        self.x2 = StoreProduct.objects.create(
            store=self.store,
            product=self.product2,
            active=False,
        )
        self.x3 = StoreProduct.objects.create(
            store=self.store2,
            product=self.product,
            active=False,
        )

    def test_model_managers(self):
        self.assertQuerySetEqual(StoreProduct.objects.all(), [self.x1])

        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                StoreProduct.all_objects.all(),
                [self.x1, self.x2, self.x3],
                ordered=False,
            )

        self.assertQuerySetEqual(self.store.storeproduct_set.all(), [self.x1])
        self.assertQuerySetEqual(self.product.storeproduct_set.all(), [self.x1])

        # for_product() takes either a Product instance or ID
        self.assertQuerySetEqual(Store.objects.for_product(self.product), [self.store])
        self.assertQuerySetEqual(
            Store.objects.for_product(self.product.id),
            [self.store],
        )
        # Chain filter() before for_product() to ensure the queryset method works
        self.assertQuerySetEqual(
            Store.objects.filter(name=self.store.name).for_product(self.product),
            [self.store],
        )

        self.assertQuerySetEqual(Product.objects.for_store(self.store), [self.product])
        self.assertQuerySetEqual(
            Product.objects.for_store(self.store.id),
            [self.product],
        )
        self.assertQuerySetEqual(
            Product.objects.filter(name=self.product.name).for_store(self.store),
            [self.product],
        )

    def test_model_managers_after_deactivation(self):
        self.x1.active = False
        self.x1.save()

        assert not self.store.storeproduct_set.all()
        assert not self.product.storeproduct_set.all()

        assert not Store.objects.for_product(self.product)
        assert not Store.objects.for_product(self.product.id)
        assert not Store.objects.filter(name=self.store.name).for_product(self.product)
        assert not Product.objects.for_store(self.store)
        assert not Product.objects.for_store(self.store.id)
        assert not (
            Product.objects.filter(name=self.product.name).for_store(self.store)
        )

    def test_prefetch_excludes_soft_deleted_objects(self):
        with self.assertNumQueries(2):
            store = Store.objects.prefetch_related("storeproduct_set").get(
                id=self.store.id,
            )

        with self.assertNumQueries(2):
            product = Product.objects.prefetch_related("storeproduct_set").get(
                id=self.product.id,
            )

        # Assert no queries to ensure all the data we need is prefetched
        with self.assertNumQueries(0):
            self.assertQuerySetEqual(store.storeproduct_set.all(), [self.x1])
            self.assertQuerySetEqual(product.storeproduct_set.all(), [self.x1])

    def test_nested_query_includes_deactivated_objects(self):
        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                Store.objects.filter(storeproduct__product=self.product),
                [self.store, self.store2],
                ordered=False,
            )


class TestActiveFilterQueryCheck(TestCase):
    def setUp(self):
        self.store = StoreFactory()
        self.product = ProductFactory()
        self.x1 = StoreProduct.objects.create(
            store=self.store,
            product=self.product,
            active=True,
        )
        self.x2 = StoreProduct.objects.create(
            store=self.store,
            product=ProductFactory(),
            active=False,
        )

    def test_raises_for_unfiltered_all_objects_queries(self):
        with pytest.raises(ActiveFilterMissingError):
            list(StoreProduct.all_objects.all())

        with pytest.raises(ActiveFilterMissingError):
            list(StoreProduct.all_objects.filter(product=self.product))

    def test_raises_for_nested_join_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.filter(storeproduct__product=self.product))

        # Should not raise
        list(
            Store.objects.filter(
                storeproduct__product=self.product,
                storeproduct__active=True,
            )
        )

    def test_raises_for_annotation_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.annotate(cnt=Count("storeproduct")))

        # Should not raise
        list(
            Store.objects.annotate(
                cnt=Count(
                    "storeproduct",
                    filter=Q(storeproduct__active=True),
                )
            )
        )

    def test_raises_for_annotated_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                Store.objects.filter(
                    id__in=Store.objects.for_product(self.product)
                ).annotate(cnt=Count("storeproduct"))
            )

        # Should not raise
        list(
            Store.objects.filter(
                id__in=Store.objects.for_product(self.product)
            ).annotate(
                cnt=Count(
                    "storeproduct",
                    filter=Q(storeproduct__active=True),
                )
            )
        )

    def test_raises_for_single_level_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(StoreProduct.objects.filter(id__in=StoreProduct.all_objects.all()))

        with pytest.raises(ActiveFilterMissingError):
            list(
                StoreProduct.objects.filter(
                    id__in=StoreProduct.all_objects.filter(product=self.product)
                )
            )

        # Should not raise
        list(StoreProduct.objects.filter(id__in=StoreProduct.objects.all()))

    def test_raises_for_double_nested_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.all_objects.all()
                    )
                )
            )

        # Should not raise
        list(
            StoreProduct.objects.filter(
                id__in=StoreProduct.objects.filter(id__in=StoreProduct.objects.all())
            )
        )

    def test_raises_for_triple_nested_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.filter(
                            id__in=StoreProduct.all_objects.all()
                        )
                    )
                )
            )

        # Should not raise
        list(
            StoreProduct.objects.filter(
                id__in=StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.all()
                    )
                )
            )
        )

    def test_raises_for_deeply_nested_subquery_without_active_filter(self):
        """
        This test ensures two-letter Django-style SQL aliases (e.g., AA0)
        are handled correctly.
        """
        with pytest.raises(ActiveFilterMissingError):
            list(
                StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.filter(
                            id__in=StoreProduct.objects.filter(
                                id__in=StoreProduct.objects.filter(
                                    id__in=StoreProduct.objects.filter(
                                        id__in=StoreProduct.objects.filter(
                                            id__in=StoreProduct.all_objects.all()
                                        )
                                    )
                                )
                            )
                        )
                    )
                )
            )

        # Should not raise
        list(
            StoreProduct.objects.filter(
                id__in=StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.filter(
                            id__in=StoreProduct.objects.filter(
                                id__in=StoreProduct.objects.filter(
                                    id__in=StoreProduct.objects.filter(
                                        id__in=StoreProduct.objects.all()
                                    )
                                )
                            )
                        )
                    )
                )
            )
        )

    def test_disable_active_filter_query_check(self):
        # Disabling the check allows unsafe queries
        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                Store.objects.filter(storeproduct__product=self.product),
                [self.store],
            )

        # The check is re-enabled after the context manager
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.filter(storeproduct__product=self.product))

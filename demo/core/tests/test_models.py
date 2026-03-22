import pytest
from django.db.models import Count, Min, Q
from django.test import TestCase
from inline_snapshot import snapshot
from inline_snapshot_django import snapshot_queries

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

        self.x1 = StoreProduct.objects.create(store=self.store, product=self.product, active=True)
        self.x2 = StoreProduct.objects.create(store=self.store, product=self.product2, active=False)
        self.x3 = StoreProduct.objects.create(store=self.store2, product=self.product, active=False)

    def test_model_managers(self):
        with snapshot_queries() as snap:
            self.assertQuerySetEqual(StoreProduct.objects.all(), [self.x1])
        assert snap == snapshot(["SELECT ... FROM core_storeproduct WHERE ..."])

        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                StoreProduct.all_objects.all(), [self.x1, self.x2, self.x3], ordered=False
            )

        self.assertQuerySetEqual(self.store.storeproduct_set.all(), [self.x1])
        self.assertQuerySetEqual(self.product.storeproduct_set.all(), [self.x1])

        # for_product() takes either a Product instance or ID
        self.assertQuerySetEqual(Store.objects.for_product(self.product), [self.store])
        with snapshot_queries() as snap:
            self.assertQuerySetEqual(Store.objects.for_product(self.product.id), [self.store])
        assert snap == snapshot(
            ["SELECT ... FROM core_store INNER JOIN core_storeproduct ON ... WHERE ..."]
        )

        # Chain filter() before for_product() to ensure the queryset method works
        self.assertQuerySetEqual(
            Store.objects.filter(name=self.store.name).for_product(self.product), [self.store]
        )

        self.assertQuerySetEqual(Product.objects.for_store(self.store), [self.product])
        with snapshot_queries() as snap:
            self.assertQuerySetEqual(Product.objects.for_store(self.store.id), [self.product])
        assert snap == snapshot(
            ["SELECT ... FROM core_product INNER JOIN core_storeproduct ON ... WHERE ..."]
        )
        self.assertQuerySetEqual(
            Product.objects.filter(name=self.product.name).for_store(self.store), [self.product]
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
        assert not Product.objects.filter(name=self.product.name).for_store(self.store)

    def test_prefetch_excludes_inactive_objects(self):
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

    ############################################
    # TEST QUERY CHECK
    ############################################

    def test_raises_for_unfiltered_all_objects_queries(self):
        with pytest.raises(ActiveFilterMissingError):
            list(StoreProduct.all_objects.all())

        with pytest.raises(ActiveFilterMissingError):
            list(StoreProduct.all_objects.filter(product=self.product))

    def test_raises_for_nested_join_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.filter(storeproduct__product=self.product))

        # Should not raise
        list(Store.objects.filter(storeproduct__product=self.product, storeproduct__active=True))

    def test_raises_for_cnt_annotation_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.annotate(cnt=Count("storeproduct")))

        # Should not raise
        self.assertQuerySetEqual(
            Store.objects.annotate(
                product_count=Count("storeproduct", filter=Q(storeproduct__active=True))
            ).values_list("name", "product_count"),
            [
                (self.store.name, 1),
                (self.store2.name, 0),
            ],
            ordered=False,
        )

        # Filtering before annotating is slightly different because it will exclude stores entirely
        # if they have no active products, instead of showing them with a count of 0.
        self.assertQuerySetEqual(
            Store.objects.filter(storeproduct__active=True)
            .annotate(product_count=Count("storeproduct"))
            .values_list("name", "product_count"),
            [
                (self.store.name, 1),
            ],
            ordered=False,
        )

        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                Store.objects.annotate(product_count=Count("storeproduct")).values_list(
                    "name", "product_count"
                ),
                [
                    (self.store.name, 2),
                    (self.store2.name, 1),
                ],
                ordered=False,
            )

    def test_raises_for_min_annotation_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.annotate(first_product_added=Min("storeproduct__created_at")))

        # Should not raise
        self.assertQuerySetEqual(
            Store.objects.annotate(
                first_product_added=Min(
                    "storeproduct__created_at", filter=Q(storeproduct__active=True)
                )
            ).values_list("name", "first_product_added"),
            [
                (self.store.name, self.x1.created_at),
                (self.store2.name, None),
            ],
            ordered=False,
        )

        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                Store.objects.annotate(
                    first_product_added=Min("storeproduct__created_at")
                ).values_list("name", "first_product_added"),
                [
                    (self.store.name, self.x1.created_at),
                    (self.store2.name, self.x3.created_at),
                ],
                ordered=False,
            )

    def test_raises_for_cnt_and_min_annotation_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                Store.objects.annotate(
                    product_count=Count("storeproduct"),
                    first_product_added=Min("storeproduct__created_at"),
                )
            )

        # Should not raise
        self.assertQuerySetEqual(
            Store.objects.annotate(
                product_count=Count("storeproduct", filter=Q(storeproduct__active=True)),
                first_product_added=Min(
                    "storeproduct__created_at", filter=Q(storeproduct__active=True)
                ),
            ).values_list("name", "product_count", "first_product_added"),
            [
                (self.store.name, 1, self.x1.created_at),
                (self.store2.name, 0, None),
            ],
            ordered=False,
        )
        self.assertQuerySetEqual(
            Store.objects.filter(storeproduct__active=True)
            .annotate(
                product_count=Count("storeproduct"),
                first_product_added=Min("storeproduct__created_at"),
            )
            .values_list("name", "product_count", "first_product_added"),
            [
                (self.store.name, 1, self.x1.created_at),
            ],
            ordered=False,
        )

        with disable_active_filter_query_check():
            self.assertQuerySetEqual(
                Store.objects.annotate(
                    product_count=Count("storeproduct"),
                    first_product_added=Min("storeproduct__created_at"),
                ).values_list("name", "product_count", "first_product_added"),
                [
                    (self.store.name, 2, self.x1.created_at),
                    (self.store2.name, 1, self.x3.created_at),
                ],
                ordered=False,
            )

    def test_raises_for_annotated_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                Store.objects.filter(id__in=Store.objects.for_product(self.product)).annotate(
                    cnt=Count("storeproduct")
                )
            )

        # Should not raise
        list(
            Store.objects.filter(id__in=Store.objects.for_product(self.product)).annotate(
                cnt=Count("storeproduct", filter=Q(storeproduct__active=True))
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
                        id__in=StoreProduct.all_objects.all(),
                    )
                )
            )

        # Should not raise
        list(
            StoreProduct.objects.filter(
                id__in=StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.all(),
                )
            )
        )

    def test_raises_for_triple_nested_subquery_without_active_filter(self):
        with pytest.raises(ActiveFilterMissingError):
            list(
                StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.filter(
                            id__in=StoreProduct.all_objects.all(),
                        )
                    )
                )
            )

        # Should not raise
        list(
            StoreProduct.objects.filter(
                id__in=StoreProduct.objects.filter(
                    id__in=StoreProduct.objects.filter(
                        id__in=StoreProduct.objects.all(),
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
                                            id__in=StoreProduct.all_objects.all(),
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
                                        id__in=StoreProduct.objects.all(),
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
                [self.store, self.store2],
                ordered=False,
            )

        # The check is re-enabled after the context manager
        with pytest.raises(ActiveFilterMissingError):
            list(Store.objects.filter(storeproduct__product=self.product))

    def test_handle_empty_result_set(self):
        self.assertQuerySetEqual(StoreProduct.objects.none(), [])

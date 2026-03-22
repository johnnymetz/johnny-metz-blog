from django.db import models


class StoreQuerySet(models.QuerySet):
    def for_product(self, product):
        """
        Store.objects.for_product(product) generates the following SQL query:

        SELECT * FROM Store
        INNER JOIN StoreProduct ON Store.id=StoreProduct.store_id
        WHERE StoreProduct.product_id=<product.id> AND StoreProduct.active;

        Args:
            product: A Product instance or ID to filter stores by.
        """
        return self.filter(
            storeproduct__product=product,
            storeproduct__active=True,
        )


class Store(models.Model):
    name = models.CharField(max_length=255)
    # Relation traversal (e.g. store.products.all()) bypasses StoreProduct's manager,
    # so inactive members leak.
    # products = models.ManyToManyField("Product", through="StoreProduct")

    objects = StoreQuerySet.as_manager()

    def __str__(self):
        return self.name


class ProductQuerySet(models.QuerySet):
    def for_store(self, store):
        """
        Product.objects.for_store(store) generates the following SQL query:

        SELECT * FROM Product
        INNER JOIN StoreProduct ON Product.id=StoreProduct.product_id
        WHERE StoreProduct.store_id=<store.id> AND StoreProduct.active;

        Args:
            store: A Store instance or ID to filter products by.
        """
        return self.filter(
            storeproduct__store=store,
            storeproduct__active=True,
        )


class Product(models.Model):
    name = models.CharField(max_length=255)

    objects = ProductQuerySet.as_manager()

    def __str__(self):
        return self.name


class StoreProductManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(active=True)


class StoreProduct(models.Model):
    store = models.ForeignKey(Store, on_delete=models.CASCADE)
    product = models.ForeignKey(Product, on_delete=models.CASCADE)
    active = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)
    # deactivated_at = models.DateTimeField(null=True, blank=True)

    objects = StoreProductManager()
    all_objects = models.Manager()  # noqa: DJ012

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["store", "product"],
                name="store_product_uniq",
            ),
        ]
        # default_manager_name = "all_objects"  # Breaks tests
        # base_manager_name = "all_objects"  # No effect on tests

    def __str__(self):
        return f"{self.store.name} <-> {self.product.name}"

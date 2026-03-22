from django.contrib import admin

from core.models import Product, Store, StoreProduct


@admin.register(Product)
class ProductAdmin(admin.ModelAdmin):
    pass


@admin.register(Store)
class StoreAdmin(admin.ModelAdmin):
    pass


@admin.register(StoreProduct)
class StoreProductAdmin(admin.ModelAdmin):
    list_display = ("__str__", "active")
    ordering = ("id",)

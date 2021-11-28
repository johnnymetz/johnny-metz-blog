from django.urls import include, path

from rest_framework.routers import DefaultRouter

from choices.views import DeviceViewSet

router = DefaultRouter()
router.register("devices", DeviceViewSet)

urlpatterns = [
    path("", include(router.urls)),
]

from django.urls import include, path

from rest_framework.routers import DefaultRouter

from choices.views import (
    CreateDeviceAPIView,
    CreateDeviceGenericAPIView,
    DeviceViewSet,
    Index,
)

router = DefaultRouter()
router.register("devices", DeviceViewSet)

urlpatterns = [
    path("index/", Index.as_view()),
    path("api/", include(router.urls)),
    path("api/devices2/", CreateDeviceGenericAPIView.as_view()),
    path("api/devices3/", CreateDeviceAPIView.as_view()),
]

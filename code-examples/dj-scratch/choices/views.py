from rest_framework.viewsets import ModelViewSet

from choices.models import Device
from choices.serializers import DeviceSerializer

# what does create options path:
# - ModelViewSet

# what does NOT create options path:
# - ReadOnlyModelViewSet


class DeviceViewSet(ModelViewSet):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer

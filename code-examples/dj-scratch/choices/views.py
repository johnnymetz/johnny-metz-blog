from rest_framework import status
from rest_framework.generics import CreateAPIView
from rest_framework.response import Response
from rest_framework.views import APIView
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


class CreateDeviceGenericAPIView(CreateAPIView):
    queryset = Device.objects.all()
    serializer_class = DeviceSerializer


class CreateDeviceAPIView(APIView):
    def post(self, request):
        device = Device.objects.create(name="Name", size=Device.Size.MEDIUM)
        return Response(DeviceSerializer(device).data, status=status.HTTP_202_ACCEPTED)


class Index(APIView):
    def get(self, request):
        return Response("Hello world")

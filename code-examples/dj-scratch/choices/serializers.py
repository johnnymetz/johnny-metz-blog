from rest_framework import serializers

from choices.models import Device


class DeviceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Device
        fields = "__all__"

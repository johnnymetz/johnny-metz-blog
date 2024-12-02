from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from files.models import File, FilePreUpload


class FileSerializer(serializers.ModelSerializer):
    download_url = serializers.URLField(read_only=True)

    user = serializers.HiddenField(default=serializers.CurrentUserDefault())

    class Meta:
        model = File
        fields = [
            "id",
            "download_url",
            "user",
            "filename",
            "is_uploaded",
            "created_at",
            "updated_at",
        ]


class FilePreUploadSerializer(DataclassSerializer):
    file = FileSerializer()
    upload_url = serializers.URLField()

    class Meta:
        dataclass = FilePreUpload

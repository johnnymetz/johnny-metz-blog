# File Upload Post

## Links

- https://django.wtf/blog/file-uploads-with-django-drf/

## Titles

- Create a File Upload API with Django & DRF
- File Uploads with Django & DRF

Write a blog post titled "File Upload API with Django & DRF".

- I have a sequence diagram of the file upload process. Walk through it and explain each item below in a sentence or two:

  - Why we're using cloud storage instead of storing the files on the server
  - Why we're using presigned URL's and forcing the client to upload the file directly to cloud storage instead of proxying through our server.

- We're using the following pip packages (write a sentence about why we're using each)..

  - Django
  - djangorestframework
  - djangorestframework-dataclasses
  - django-storages
  - boto3: Because we're using S3 for cloud storage.

- Create the models:

```python
from dataclasses import dataclass
from pathlib import Path

from django.contrib.auth.models import User
from django.db import models
from django.db.models.signals import post_delete
from django.dispatch import receiver
from django.urls import reverse

from storages.backends.s3boto3 import S3Boto3Storage


def filename_factory(instance: "File", filename: str) -> str:
    extension = Path(filename).suffix
    return f"{instance.pk}{extension}"


class File(models.Model):
    file = models.FileField(
        upload_to=filename_factory,
        storage=S3Boto3Storage(),
        # Don't set null=True because FileField is a varchar field under the hood, and you shouldn't use
        # null=True on varchar fields, see https://docs.djangoproject.com/en/5.1/ref/models/fields/#null
        blank=True,
    )
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    # This is different from the cloud storage filename
    filename = models.CharField(max_length=255, blank=True)
    is_uploaded = models.BooleanField(
        default=False, help_text="True if the file is uploaded to cloud storage"
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def get_absolute_url(self):
        return reverse("file-detail", args=[self.pk])


@receiver(post_delete, sender=File)
def delete_s3_file(**kwargs):
    """Delete the file from S3 after the object is deleted."""
    # save=False because we don't need to save the object we just deleted
    kwargs["instance"].file.delete(save=False)


@dataclass
class FilePreUpload:
    """
    A file that has been created in the database but not yet uploaded to cloud storage.
    Includes a presigned URL and any fields required to upload the file.
    """

    file: File
    upload_url: str
    fields: dict
```

- Create the serializers:

```python
from rest_framework import serializers
from rest_framework_dataclasses.serializers import DataclassSerializer

from files.models import File, FilePreUpload


class FileSerializer(serializers.ModelSerializer):
    download_url = serializers.SerializerMethodField()

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

    def get_download_url(self, obj):
        return self.context["request"].build_absolute_uri(obj.get_absolute_url())


class FilePreUploadSerializer(DataclassSerializer):
    file = FileSerializer()
    upload_url = serializers.URLField()

    class Meta:
        dataclass = FilePreUpload
```

- Create the views:

```python
from django.core.exceptions import ValidationError
from django.shortcuts import redirect

from rest_framework import serializers as drf_serializers
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ModelViewSet

from files.models import File
from files.serializers import FilePreUploadSerializer, FileSerializer

# 100 MB in bytes. This is what GitHub uses for their file upload size limit.
MAX_FILE_SIZE = 100 * pow(2, 20)


class FileView(ModelViewSet):
    permission_classes = [IsAuthenticated]

    def get_serializer_class(self):
        if self.action == "create":
            return FilePreUploadSerializer
        return FileSerializer

    def get_queryset(self):
        return File.objects.filter(user=self.request.user)

    def create(self, request, *args, **kwargs):
        filename = request.data.get("filename")

        if not filename:
            raise drf_serializers.ValidationError(
                {"filename": ["This field is required."]}
            )

        try:
            file = File.objects.create(filename=filename, user=request.user)
        except ValidationError as exc:
            raise drf_serializers.ValidationError(
                drf_serializers.as_serializer_error(exc)
            )

        s3_filename = File.file.field.generate_filename(
            instance=file, filename=filename
        )
        file.file.name = s3_filename
        file.save()

        # https://boto3.amazonaws.com/v1/documentation/api/latest/reference/services/s3/client/generate_presigned_post.html
        presigned_response = (
            file.file.storage.connection.meta.client.generate_presigned_post(
                Bucket=file.file.storage.bucket_name,
                Key=s3_filename,
                Conditions=[
                    ["content-length-range", 0, MAX_FILE_SIZE],
                ],
            )
        )

        presigned_response["file"] = file
        presigned_response["upload_url"] = presigned_response.pop("url")

        serializer = self.get_serializer(presigned_response)

        return Response(serializer.data, status=status.HTTP_201_CREATED)

    def retrieve(self, request, *args, **kwargs):
        if self.request.query_params.get("meta", "").lower() == "true":
            return super().retrieve(request, *args, **kwargs)

        file = self.get_object()

        from django.http import Http404

        if not file.is_uploaded:
            raise Http404("File has not been uploaded yet")

        return redirect(file.file.url)
```

- Here's a script to test the API:

```python
BASE_URL = "http://localhost:8000"

# Create the file
filename = "masters.jpeg"
response = requests.post(
    f"{BASE_URL}/files/",
    headers={"Authorization": f"Token {token}"},
    json={"filename": filename},
)
response.raise_for_status()

# Upload the file to S3
with open(f"./{filename}", "rb") as f:
    data = f.read()
response = requests.post(
    url=response_data["upload_url"],
    data=response_data["fields"],
    files={"file": data},
)
response.raise_for_status()

# Mark file as uploaded
response = requests.patch(
    response_data["file"]["download_url"],
    headers={"Authorization": f"Token {token}"},
    json={"is_uploaded": True},
)
response.raise_for_status()
```

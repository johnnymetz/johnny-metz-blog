from dataclasses import dataclass
from pathlib import Path

from django.conf import settings
from django.contrib.auth.models import User
from django.db import models
from django.urls import reverse

from .storages import FileStorage


def filename_factory(instance: "File", filename: str) -> str:
    extension = Path(filename).suffix
    return f"{instance.pk}{extension}"


class File(models.Model):
    file = models.FileField(
        upload_to=filename_factory,
        storage=FileStorage(),
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

    @property
    def download_url(self):
        path = reverse("file-detail", args=[self.pk])
        return f"{settings.SERVICE_URL}{path}"


@dataclass
class FilePreUpload:
    """
    A file that has been created in the database but not yet uploaded to cloud storage.
    Includes a presigned URL and any fields required to upload the file.
    """

    file: File
    upload_url: str
    fields: dict

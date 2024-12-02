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

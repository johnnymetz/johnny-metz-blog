from storages.backends.s3boto3 import S3Boto3Storage


class FileStorage(S3Boto3Storage):
    bucket_name = "my-bucket"

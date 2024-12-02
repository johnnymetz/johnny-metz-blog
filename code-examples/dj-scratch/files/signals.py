from django.db.models.signals import post_delete
from django.dispatch import receiver

from files.models import File


@receiver(post_delete, sender=File)
def delete_s3_file(**kwargs):
    """Delete the file from S3 after the object is deleted."""
    # save=False because we don't need to save the object we just deleted
    kwargs["instance"].file.delete(save=False)

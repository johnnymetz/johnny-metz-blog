from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from core import models


@receiver(post_save, sender=models.TeamUser)
@receiver(post_delete, sender=models.TeamUser)
def invalidate_cache(sender, instance, **kwargs):
    # if "team" in team_user._state.fields_cache:
    if sender.team.is_cached(instance):
        try:
            del instance.team.total_points
        except AttributeError:
            pass

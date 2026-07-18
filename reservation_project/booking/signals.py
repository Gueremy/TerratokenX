from django.contrib.auth.models import User
from django.db.models.signals import post_save
from django.dispatch import receiver

from .models import UserProfile


@receiver(post_save, sender=User)
def crear_userprofile(sender, instance, created, **kwargs):
    """Garantiza que todo User tenga su UserProfile asociado."""
    if created:
        UserProfile.objects.get_or_create(user=instance)

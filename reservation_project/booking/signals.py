from django.contrib.auth.models import User
from django.core.cache import cache
from django.db.models.signals import post_delete, post_save
from django.dispatch import receiver

from .models import FeeConfig, Proyecto, TierConfig, UserProfile


@receiver(post_save, sender=User)
def crear_userprofile(sender, instance, created, **kwargs):
    """Garantiza que todo User tenga su UserProfile asociado."""
    if created:
        UserProfile.objects.get_or_create(user=instance)


# ── Invalidación de caché ────────────────────────────────────────────────────

@receiver([post_save, post_delete], sender=Proyecto)
def invalidar_cache_marketplace(sender, instance, **kwargs):
    cache.delete('marketplace_proyectos')
    cache.delete(f'proyecto_{instance.slug}')


@receiver([post_save, post_delete], sender=TierConfig)
def invalidar_cache_tiers(sender, instance, **kwargs):
    cache.delete('tier_config_all')


@receiver([post_save, post_delete], sender=FeeConfig)
def invalidar_cache_fees(sender, instance, **kwargs):
    cache.delete('fee_config_all')

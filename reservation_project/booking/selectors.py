"""Capa de selectors: TODAS las queries reutilizables viven aquí.

Los selectors no contienen lógica de negocio — solo construyen querysets.
"""

from django.core.cache import cache
from django.utils import timezone

from .models import FeeConfig, ProjectDrop, Proyecto, Reserva, TierConfig


# ── Drops ────────────────────────────────────────────────────────────────────

def get_drop_activo(proyecto_id: int):
    """
    Devuelve el Drop activo del proyecto, o None si no hay ninguno.
    Un Drop es activo si:
      - activo=True
      - fecha_inicio <= now() <= fecha_fin
      - stock_disponible > 0
    """
    ahora = timezone.now()
    return ProjectDrop.objects.filter(
        proyecto_id=proyecto_id,
        activo=True,
        fecha_inicio__lte=ahora,
        fecha_fin__gte=ahora,
        stock_disponible__gt=0,
    ).select_related('proyecto').first()


def get_stock_disponible(drop_id: int) -> int:
    """Devuelve el stock disponible del Drop. Lanza DoesNotExist si no existe."""
    return ProjectDrop.objects.values_list('stock_disponible', flat=True).get(id=drop_id)


def list_drops_proyecto(proyecto_id: int):
    """Todos los drops de un proyecto, ordenados por número."""
    return ProjectDrop.objects.filter(proyecto_id=proyecto_id).order_by('numero')


# ── Reservas ─────────────────────────────────────────────────────────────────

def get_reserva_por_payment_id(payment_id: str):
    """Reserva asociada a un pago de MercadoPago, o None."""
    return Reserva.objects.select_related('user', 'proyecto').filter(
        mp_payment_id=payment_id
    ).first()


def get_reserva_por_cryptomus_uuid(uuid: str):
    """Reserva asociada a un invoice de Cryptomus, o None."""
    return Reserva.objects.select_related('user', 'proyecto').filter(
        cryptomus_uuid=uuid
    ).first()


def list_reservas_usuario(user_id: int):
    """Historial de reservas de un usuario."""
    return Reserva.objects.filter(user_id=user_id).select_related(
        'proyecto'
    ).order_by('-created_at')


# ── Configuración cacheada (tiers / fees / marketplace) ──────────────────────

def get_tier_config_all() -> list:
    """TierConfig raramente cambia — cachear 1 hora."""
    return cache.get_or_set(
        'tier_config_all',
        lambda: list(TierConfig.objects.all().order_by('tier').values()),
        timeout=3600,
    )


def get_fee_config_all() -> list:
    """FeeConfig igual — cachear 1 hora."""
    return cache.get_or_set(
        'fee_config_all',
        lambda: list(FeeConfig.objects.filter(activo=True).values()),
        timeout=3600,
    )


def get_marketplace_proyectos():
    """Marketplace público — cachear 5 minutos."""
    return cache.get_or_set(
        'marketplace_proyectos',
        lambda: list(
            Proyecto.objects.filter(activo=True)
            .prefetch_related('drops', 'imagenes')
        ),
        timeout=300,
    )

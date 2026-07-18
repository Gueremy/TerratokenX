# Redis y Celery — TerraTokenX

## Redis tiene dos roles

1. **Caché** → datos que se leen frecuente y cambian poco (tiers, fees, marketplace)
2. **Celery broker** → cola de tareas en background (emails, webhooks, expiración créditos)

Misma instancia Redis para los dos. En Render: Redis add-on (~$7/mes plan Starter).

---

## Qué cachear y por cuánto tiempo

```python
# booking/selectors.py — patrón cache.get_or_set

from django.core.cache import cache


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


def get_marketplace_proyectos() -> list:
    """Marketplace público — cachear 5 minutos."""
    return cache.get_or_set(
        'marketplace_proyectos',
        lambda: list(
            Proyecto.objects.filter(activo=True)
            .select_related('owner')
            .prefetch_related('drops', 'imagenes')
            .only('id', 'nombre', 'slug', 'precio_token',
                  'tokens_totales', 'tokens_vendidos', 'owner_type')
        ),
        timeout=300,
    )
```

**Qué NO cachear:** saldos de créditos, reservas activas, datos de sesión de usuario, respuestas de webhooks.

---

## Invalidación de caché

```python
# booking/signals.py

from django.db.models.signals import post_save
from django.dispatch import receiver
from django.core.cache import cache


@receiver(post_save, sender=Proyecto)
def invalidar_cache_marketplace(sender, instance, **kwargs):
    cache.delete('marketplace_proyectos')
    cache.delete(f'proyecto_{instance.slug}')


@receiver(post_save, sender=TierConfig)
def invalidar_cache_tiers(sender, instance, **kwargs):
    cache.delete('tier_config_all')


@receiver(post_save, sender=FeeConfig)
def invalidar_cache_fees(sender, instance, **kwargs):
    cache.delete('fee_config_all')
```

---

## Celery — configuración

```python
# terratokenx/celery.py
import os
from celery import Celery
from celery.schedules import crontab

os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'terratokenx.settings.local')
app = Celery('terratokenx')
app.config_from_object('django.conf:settings', namespace='CELERY')
app.autodiscover_tasks()

# Beat schedule — tareas periódicas
app.conf.beat_schedule = {
    'expirar-creditos-diario': {
        'task': 'booking.tasks.expirar_creditos_vencidos',
        'schedule': crontab(hour=2, minute=0),   # 2 AM Chile
    },
    'notificar-creditos-por-vencer': {
        'task': 'booking.tasks.notificar_creditos_por_vencer',
        'schedule': crontab(hour=9, minute=0),   # 9 AM Chile, diario
    },
    'sync-tokens-vendidos': {
        'task': 'booking.tasks.sync_tokens_vendidos',
        'schedule': crontab(minute='*/15'),       # cada 15 min
    },
}
```

```python
# terratokenx/__init__.py
from .celery import app as celery_app
__all__ = ('celery_app',)
```

---

## Todas las tasks de Fase 1

```python
# booking/tasks.py
from celery import shared_task
from django.db import transaction
from django.utils import timezone
from decimal import Decimal


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def procesar_pago_mp_task(self, payment_id: str):
    """Consulta el pago en MP y confirma la reserva si está aprobado."""
    try:
        from .services import confirmar_reserva
        from .selectors import get_reserva_por_mp_payment
        # ... implementación en docs/negocio/pagos.md
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def procesar_pago_confirmado_crypto_task(self, order_id: str, uuid: str):
    """Confirma reserva tras pago Cryptomus."""
    try:
        from .services import confirmar_reserva
        reserva = Reserva.objects.get(id=order_id)
        if reserva.estado_pago == EstadoPago.CONFIRMADO:
            return   # idempotencia
        reserva.cryptomus_uuid = uuid
        reserva.save(update_fields=['cryptomus_uuid'])
        confirmar_reserva(reserva.id)
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def enviar_email_confirmacion_task(reserva_id: int):
    """Email de confirmación — async para no bloquear la confirmación."""
    from .integrations.resend import enviar_confirmacion_reserva
    reserva = Reserva.objects.select_related('user', 'proyecto').get(id=reserva_id)
    enviar_confirmacion_reserva(reserva)


@shared_task
def expirar_creditos_vencidos():
    """Corre diariamente a las 2 AM — expira créditos vencidos."""
    # Implementación completa en docs/negocio/creditos-tiers.md
    pass


@shared_task
def notificar_creditos_por_vencer():
    """Notifica usuarios cuyos créditos vencen en los próximos 7 días."""
    desde = timezone.now()
    hasta = desde + timezone.timedelta(days=7)
    balances = CreditBalance.objects.filter(
        expires_at__range=(desde, hasta),
        balance_usd__gt=0,
    ).select_related('user')

    for balance in balances:
        from .integrations.resend import enviar_creditos_por_vencer
        enviar_creditos_por_vencer(balance.user, balance)


@shared_task
def sync_tokens_vendidos():
    """
    Sincroniza tokens_vendidos en Proyecto con la suma real de Reservas confirmadas.
    Por si hubo discrepancias.
    """
    from django.db.models import Sum, Count
    proyectos = Proyecto.objects.annotate(
        vendidos_real=Sum(
            'reserva__cantidad_tokens',
            filter=models.Q(reserva__estado_pago=EstadoPago.CONFIRMADO)
        )
    ).filter(activo=True)

    for proyecto in proyectos:
        if proyecto.vendidos_real is not None:
            Proyecto.objects.filter(id=proyecto.id).update(
                tokens_vendidos=proyecto.vendidos_real
            )
```

---

## Correr Celery en desarrollo

```bash
# Terminal 1 — worker
celery -A terratokenx worker --loglevel=info

# Terminal 2 — beat (scheduler de crons)
celery -A terratokenx beat --loglevel=info --scheduler django_celery_beat.schedulers:DatabaseScheduler

# En Render — se configura como proceso separado (Render Worker)
# Comando: celery -A terratokenx worker --beat --loglevel=info
```

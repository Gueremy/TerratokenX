"""Celery tasks — thin wrappers de services. Llaman un service y manejan el retry."""

import logging
from decimal import Decimal

from celery import shared_task
from django.db import transaction
from django.utils import timezone

logger = logging.getLogger('booking')


# ── Pagos ────────────────────────────────────────────────────────────────────

@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def procesar_pago_mp_task(self, payment_id: str):
    """Consulta el pago en MercadoPago y confirma la reserva si está aprobado."""
    try:
        import mercadopago
        from django.conf import settings

        from .constants import EstadoPago
        from .exceptions import IdempotenciaError
        from .models import Reserva
        from .services import confirmar_reserva

        sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)
        payment = sdk.payment().get(payment_id)
        data = payment['response']
        status = data.get('status')

        if status != 'approved':
            logger.info("Pago MP %s con status=%s — no se procesa", payment_id, status)
            return

        reserva_id = int(data.get('external_reference', 0))
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva or reserva.estado_pago == EstadoPago.CONFIRMADO:
            return  # idempotencia

        reserva.mp_payment_id = str(payment_id)
        reserva.save(update_fields=['mp_payment_id'])
        try:
            confirmar_reserva(reserva_id)
        except IdempotenciaError:
            pass
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def procesar_pago_confirmado_crypto_task(self, order_id: str, uuid: str, paid_over: bool = False):
    """Confirma reserva tras pago Cryptomus (status paid / paid_over)."""
    try:
        from .constants import EstadoPago
        from .exceptions import IdempotenciaError
        from .models import AuditLog, Reserva
        from .services import confirmar_reserva

        reserva = Reserva.objects.filter(id=order_id).first()
        if not reserva:
            logger.warning("Webhook Cryptomus: reserva %s no existe", order_id)
            return
        if reserva.estado_pago == EstadoPago.CONFIRMADO:
            return  # idempotencia

        reserva.cryptomus_uuid = uuid
        reserva.save(update_fields=['cryptomus_uuid'])
        try:
            confirmar_reserva(reserva.id)
        except IdempotenciaError:
            return

        if paid_over:
            AuditLog.registrar(
                accion='pago.excedente',
                objeto=reserva,
                datos_despues={'uuid': uuid, 'detalle': 'paid_over: el cliente pagó de más'},
            )
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def procesar_pago_fallido_crypto_task(self, order_id: str, status: str):
    """Marca la reserva FALLIDA y devuelve el stock al Drop."""
    try:
        from .constants import EstadoPago
        from .exceptions import IdempotenciaError
        from .services import marcar_reserva_fallida

        estado = EstadoPago.RECHAZADO if status == 'cancel' else EstadoPago.FALLIDO
        try:
            marcar_reserva_fallida(int(order_id), estado, motivo=f'cryptomus:{status}')
        except IdempotenciaError:
            pass
    except Exception as exc:
        raise self.retry(exc=exc)


@shared_task
def notificar_revision_manual_task(order_id: str):
    """Status 'check' de Cryptomus: alerta a Joan para revisión manual."""
    from .models import AuditLog, Reserva

    reserva = Reserva.objects.filter(id=order_id).first()
    AuditLog.registrar(
        accion='pago.revision_manual',
        objeto=reserva,
        datos_despues={'detalle': 'Cryptomus reportó status=check — revisar manualmente'},
    )
    from .integrations.resend import enviar_alerta_admin
    enviar_alerta_admin(
        asunto=f'Revisar pago crypto — Reserva #{order_id}',
        mensaje=f'Cryptomus reportó status=check para la reserva {order_id}. Revisar en el dashboard de Cryptomus.',
    )


@shared_task(bind=True, max_retries=5, default_retry_delay=30)
def procesar_pago_kushki_task(self, reserva_id: str, estado: str):
    """Confirma o falla la reserva según el estado reportado por Kushki."""
    try:
        from .constants import EstadoPago
        from .exceptions import IdempotenciaError
        from .services import confirmar_reserva, marcar_reserva_fallida

        estado_lower = (estado or '').lower()
        try:
            if estado_lower in ('approved', 'approvedtransaction', 'success', 'completed'):
                confirmar_reserva(int(reserva_id))
            elif estado_lower in ('declined', 'failed', 'cancelled', 'void'):
                marcar_reserva_fallida(int(reserva_id), EstadoPago.FALLIDO, motivo=f'kushki:{estado}')
        except IdempotenciaError:
            pass
    except Exception as exc:
        raise self.retry(exc=exc)


# ── Emails ───────────────────────────────────────────────────────────────────

@shared_task
def enviar_email_confirmacion_task(reserva_id: int):
    """Email de confirmación — async para no bloquear la confirmación."""
    from .integrations.resend import enviar_confirmacion_reserva
    from .models import Reserva

    reserva = Reserva.objects.select_related('user', 'proyecto').get(id=reserva_id)
    enviar_confirmacion_reserva(reserva)


# ── Créditos ─────────────────────────────────────────────────────────────────

@shared_task
def expirar_creditos_vencidos():
    """Corre diariamente a las 2 AM (America/Santiago). Expira créditos vencidos."""
    from .models import CreditBalance, CreditTransaction

    count = 0
    with transaction.atomic():
        vencidos = CreditBalance.objects.select_for_update().filter(
            expires_at__lt=timezone.now(),
            balance_usd__gt=0,
        )
        for balance in vencidos:
            monto_expirado = balance.balance_usd
            CreditTransaction.objects.create(
                user=balance.user,
                tipo='EXPIRACION',
                monto_usd=monto_expirado,
                descripcion='Créditos expirados automáticamente',
            )
            balance.balance_usd = Decimal('0.00')
            balance.save(update_fields=['balance_usd'])
            count += 1

    return f"Créditos expirados para {count} usuarios"


@shared_task
def notificar_creditos_por_vencer():
    """Notifica usuarios cuyos créditos vencen en los próximos 7 días."""
    from .integrations.resend import enviar_creditos_por_vencer
    from .models import CreditBalance

    desde = timezone.now()
    hasta = desde + timezone.timedelta(days=7)
    balances = CreditBalance.objects.filter(
        expires_at__range=(desde, hasta),
        balance_usd__gt=0,
    ).select_related('user')

    for balance in balances:
        enviar_creditos_por_vencer(balance.user, balance)

    return f"Notificados {balances.count()} usuarios"


# ── Mantenimiento ────────────────────────────────────────────────────────────

@shared_task
def sync_tokens_vendidos():
    """
    Sincroniza tokens_vendidos en Proyecto con la suma real de reservas
    confirmadas, por si hubo discrepancias.
    """
    from .models import Proyecto

    for proyecto in Proyecto.objects.filter(activo=True):
        vendidos_real = proyecto.calcular_tokens_vendidos()
        if proyecto.tokens_vendidos != vendidos_real:
            Proyecto.objects.filter(id=proyecto.id).update(tokens_vendidos=vendidos_real)

    return "sync ok"


# ── KYC (Didit) ──────────────────────────────────────────────────────────────

@shared_task
def procesar_kyc_aprobado_task(user_id: str, completed_steps: list):
    """Actualiza el tier del usuario tras aprobación de Didit."""
    from .constants import TIER_NOMBRES
    from .models import AuditLog, UserProfile

    # Determinar tier según checks completados (T4 Black requiere aprobación manual de Joan)
    tier_nuevo = 3 if 'aml_screening' in (completed_steps or []) else 2

    perfil = UserProfile.objects.select_related('user').get(user_id=user_id)

    # Verificación adicional contra Registro Civil para chilenos (no bloqueante)
    if (perfil.rut or '').strip():
        from .integrations.floid import verificar_rut_registro_civil
        verificar_rut_registro_civil(perfil.rut)

    perfil.kyc_tier = tier_nuevo
    perfil.kyc_status = UserProfile.KYC_APROBADO
    perfil.kyc_verificado_en = timezone.now()
    perfil.save(update_fields=['kyc_tier', 'kyc_status', 'kyc_verificado_en'])

    AuditLog.registrar(
        accion='kyc.aprobado',
        objeto=perfil,
        user=perfil.user,
        datos_despues={'tier': tier_nuevo, 'tier_nombre': TIER_NOMBRES[tier_nuevo], 'provider': 'didit'},
    )

    from .integrations.resend import enviar_kyc_aprobado
    enviar_kyc_aprobado(perfil.user)


@shared_task
def procesar_kyc_rechazado_task(user_id: str, decline_reasons: list):
    """Marca el KYC como rechazado y lo audita."""
    from .models import AuditLog, UserProfile

    perfil = UserProfile.objects.get(user_id=user_id)
    perfil.kyc_status = UserProfile.KYC_RECHAZADO
    perfil.save(update_fields=['kyc_status'])

    AuditLog.registrar(
        accion='kyc.rechazado',
        objeto=perfil,
        datos_despues={'motivos': decline_reasons, 'provider': 'didit'},
    )


@shared_task
def notificar_revision_manual_kyc_task(user_id: str, session_id: str):
    """Status 'review' de Didit: notificar a Joan."""
    from .integrations.resend import enviar_alerta_admin
    from .models import AuditLog

    AuditLog.registrar(
        accion='kyc.revision_manual',
        datos_despues={'user_id': user_id, 'session_id': session_id},
    )
    enviar_alerta_admin(
        asunto='KYC requiere revisión manual',
        mensaje=f'La sesión Didit {session_id} del usuario {user_id} quedó en revisión manual.',
    )

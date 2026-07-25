"""Webhooks de pasarelas de pago.

Patrón obligatorio (docs/negocio/pagos.md):
1. VERIFICAR FIRMA — siempre primero
2. Extraer identificador único
3. Idempotencia — ¿ya lo procesamos?
4. Delegar a Celery — nunca procesar en el webhook directamente
5. Responder 200 inmediatamente
"""

import hashlib
import hmac
import json
import logging

from django.conf import settings
from rest_framework.response import Response
from rest_framework.views import APIView

logger = logging.getLogger('booking.payments')


# ── MercadoPago ──────────────────────────────────────────────────────────────

def verificar_firma_mp(request) -> bool:
    """
    Verifica la firma HMAC-SHA256 del webhook de MercadoPago.

    Template oficial del manifest (los tres componentes son obligatorios):
        id:<data.id>;request-id:<x-request-id>;ts:<ts>;

    donde `ts` sale del propio header x-signature ("ts=...,v1=...").
    Omitir `ts:` produce una firma que nunca coincide con la real de MP.
    """
    secret = settings.MERCADOPAGO_WEBHOOK_SECRET
    if not secret:
        logger.warning('mp.webhook.sin_secret_configurado')
        return False

    received = request.headers.get('x-signature', '')
    partes = dict(
        part.strip().split('=', 1) for part in received.split(',') if '=' in part
    )
    ts = partes.get('ts', '')
    v1 = partes.get('v1', '')
    if not ts or not v1:
        return False

    request_id = request.headers.get('x-request-id', '')
    try:
        data_id = str(request.data.get('data', {}).get('id', ''))
    except AttributeError:
        return False

    # MP normaliza el id a minúsculas cuando es alfanumérico
    if data_id and not data_id.isdigit():
        data_id = data_id.lower()

    manifest = f"id:{data_id};request-id:{request_id};ts:{ts};"
    expected = hmac.new(secret.encode(), manifest.encode(), hashlib.sha256).hexdigest()

    return hmac.compare_digest(expected, v1)


class MPWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        if not verificar_firma_mp(request):
            logger.warning('mp.webhook.firma_invalida')
            return Response(status=403)

        if request.data.get('type') != 'payment':
            return Response(status=200)

        payment_id = str(request.data.get('data', {}).get('id', ''))
        if not payment_id:
            return Response(status=200)

        from booking.tasks import procesar_pago_mp_task
        procesar_pago_mp_task.delay(payment_id)
        return Response(status=200)


# ── Cryptomus ────────────────────────────────────────────────────────────────

class CryptomusWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        from booking.integrations.cryptomus import verificar_firma_webhook
        if not verificar_firma_webhook(request):
            logger.warning('cryptomus.webhook.firma_invalida')
            return Response(status=403)

        data = request.data
        status_pago = data.get('status')
        uuid = data.get('uuid')
        order_id = data.get('order_id')
        is_final = data.get('is_final', False)

        if not is_final:
            return Response(status=200)  # aún en proceso — esperar siguiente webhook

        from booking.tasks import (
            notificar_revision_manual_task,
            procesar_pago_confirmado_crypto_task,
            procesar_pago_fallido_crypto_task,
        )

        if status_pago == 'paid':
            procesar_pago_confirmado_crypto_task.delay(order_id, uuid)
        elif status_pago == 'paid_over':
            procesar_pago_confirmado_crypto_task.delay(order_id, uuid, paid_over=True)
        elif status_pago in ('wrong_amount', 'cancel', 'fail', 'system_fail'):
            procesar_pago_fallido_crypto_task.delay(order_id, status_pago)
        elif status_pago == 'check':
            notificar_revision_manual_task.delay(order_id)
        # 'process' u otros no finales: nada que hacer

        return Response(status=200)


# ── Kushki ───────────────────────────────────────────────────────────────────

def verificar_firma_kushki(request) -> bool:
    """Verifica la firma HMAC del webhook de Kushki (header X-Kushki-Signature)."""
    secret = settings.KUSHKI_PRIVATE_KEY
    if not secret:
        return False
    received = request.headers.get('x-kushki-signature', '')
    if not received:
        return False
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    return hmac.compare_digest(expected, received)


class KushkiWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        if not verificar_firma_kushki(request):
            logger.warning('kushki.webhook.firma_invalida')
            return Response(status=403)

        data = request.data
        estado = data.get('status') or data.get('transactionStatus')
        reserva_id = (data.get('metadata') or {}).get('reserva_id')
        if not reserva_id:
            return Response(status=200)

        from booking.tasks import procesar_pago_kushki_task
        procesar_pago_kushki_task.delay(str(reserva_id), str(estado))
        return Response(status=200)


# ── Didit (KYC) ──────────────────────────────────────────────────────────────

class DiditWebhookView(APIView):
    authentication_classes = []
    permission_classes = []
    throttle_classes = []

    def post(self, request):
        from booking.integrations.didit import verificar_firma_webhook
        if not verificar_firma_webhook(request):
            logger.warning('didit.webhook.firma_invalida',
                           extra={'ip': request.META.get('REMOTE_ADDR')})
            return Response(status=403)

        data = request.data
        user_id = data.get('vendor_data')
        status_kyc = data.get('status')  # 'approved' | 'declined' | 'review' | 'expired'
        session_id = data.get('session_id')
        completed_steps = data.get('completed_steps', [])

        logger.info('didit.webhook.recibido', extra={
            'user_id': user_id, 'status': status_kyc, 'session_id': session_id,
        })

        from booking.tasks import (
            notificar_revision_manual_kyc_task,
            procesar_kyc_aprobado_task,
            procesar_kyc_rechazado_task,
        )

        if status_kyc == 'approved':
            procesar_kyc_aprobado_task.delay(user_id, completed_steps)
        elif status_kyc == 'declined':
            procesar_kyc_rechazado_task.delay(user_id, data.get('decline_reasons', []))
        elif status_kyc == 'review':
            notificar_revision_manual_kyc_task.delay(user_id, session_id)

        return Response(status=200)

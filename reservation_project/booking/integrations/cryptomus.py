"""Cliente de Cryptomus — crypto global, +100 monedas, fee 0.4%.

Las integraciones no conocen modelos de Django: reciben y devuelven datos puros.
Docs: https://doc.cryptomus.com
"""

import base64
import hashlib
import hmac
import json
import logging

import requests
from django.conf import settings

logger = logging.getLogger('booking.payments')

API_BASE = 'https://api.cryptomus.com/v1'


def _generar_firma(payload: dict) -> str:
    body_json = json.dumps(payload, separators=(',', ':'))
    body_b64 = base64.b64encode(body_json.encode()).decode()
    return hashlib.md5(
        f"{body_b64}{settings.CRYPTOMUS_PAYMENT_API_KEY}".encode()
    ).hexdigest()


def crear_invoice(monto_usd: str, order_id: str) -> dict:
    """
    Crea un invoice en Cryptomus y devuelve el resultado
    (incluye 'url' para redirigir al usuario y 'uuid' del invoice).
    """
    payload = {
        'amount': str(monto_usd),
        'currency': 'USD',
        'order_id': str(order_id),
        'url_callback': f"{settings.BASE_URL}/api/webhooks/cryptomus/",
        'url_success': f"{settings.FRONTEND_URL}/compra/exito/",
        'url_return': f"{settings.FRONTEND_URL}/compra/",
        'is_payment_multiple': False,
        'lifetime': 3600,  # 1 hora para pagar
    }

    response = requests.post(
        f'{API_BASE}/payment',
        json=payload,
        headers={
            'merchant': settings.CRYPTOMUS_MERCHANT_ID,
            'sign': _generar_firma(payload),
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    logger.info('cryptomus.invoice.creado', extra={'order_id': order_id})
    return data['result']


def verificar_firma_webhook(request) -> bool:
    """
    Verifica la firma MD5 del webhook entrante de Cryptomus.
    El campo 'sign' viene dentro del body y se calcula sobre el body sin ese campo.
    """
    try:
        data = json.loads(request.body)
    except (json.JSONDecodeError, ValueError):
        return False

    received_sign = data.pop('sign', None)
    if not received_sign:
        return False

    body_b64 = base64.b64encode(
        json.dumps(data, separators=(',', ':')).encode()
    ).decode()
    expected = hashlib.md5(
        f"{body_b64}{settings.CRYPTOMUS_PAYMENT_API_KEY}".encode()
    ).hexdigest()
    return hmac.compare_digest(expected, received_sign)


def generar_firma_para_test(data: dict) -> str:
    """Genera la firma que Cryptomus pondría en un webhook (para tests)."""
    return _generar_firma(data)

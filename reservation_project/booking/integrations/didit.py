"""Cliente de Didit — KYC / AML / Wallet Screening.

500 verificaciones gratis/mes. Solo se cobra por verificaciones exitosas.
Docs: https://docs.didit.me
"""

import hashlib
import hmac
import logging

import requests
from django.conf import settings

logger = logging.getLogger('booking.kyc')

API_BASE = 'https://api.didit.me/v3'


def iniciar_sesion_kyc(user_id: int, tier_requerido: int) -> dict:
    """
    Crea sesión de verificación en Didit.
    Devuelve {'session_url': ..., 'session_id': ...} para redirigir al usuario.
    """
    steps = _steps_para_tier(tier_requerido)

    try:
        response = requests.post(
            f'{API_BASE}/session/',
            headers={
                'Authorization': f'Bearer {settings.DIDIT_API_KEY}',
                'Content-Type': 'application/json',
            },
            json={
                'vendor_data': str(user_id),
                'callback': settings.DIDIT_WEBHOOK_URL,
                'steps': steps,
            },
            timeout=10,
        )
        response.raise_for_status()
        data = response.json()
        logger.info('didit.session.created', extra={
            'user_id': user_id, 'session_id': data.get('session_id'),
        })
        return {
            'session_url': data['session_url'],
            'session_id': data['session_id'],
        }
    except requests.RequestException as e:
        logger.error('didit.session.error', extra={'user_id': user_id, 'error': str(e)})
        raise


def _steps_para_tier(tier: int) -> list:
    base = ['id_verification', 'passive_liveness', 'face_match']
    if tier >= 3:   # Gold o Black: también AML
        base.append('aml_screening')
    return base


def verificar_wallet(wallet_address: str) -> dict:
    """
    Verifica el riesgo de una wallet crypto antes de registrarla (Fase 3).
    Devuelve {'risk_score': 0-100, 'flagged': bool}.
    """
    try:
        response = requests.post(
            f'{API_BASE}/wallet-screening/',
            headers={'Authorization': f'Bearer {settings.DIDIT_API_KEY}'},
            json={'address': wallet_address},
            timeout=10,
        )
        response.raise_for_status()
        return response.json()
    except requests.RequestException as e:
        logger.error('didit.wallet.error', extra={'wallet': wallet_address, 'error': str(e)})
        # En caso de error: bloquear por precaución, no asumir wallet limpia
        return {'risk_score': 100, 'flagged': True, 'error': str(e)}


def verificar_firma_webhook(request) -> bool:
    """Verifica la firma HMAC-SHA256 del webhook de Didit."""
    secret = settings.DIDIT_WEBHOOK_SECRET
    if not secret:
        return False
    expected = hmac.new(secret.encode(), request.body, hashlib.sha256).hexdigest()
    received = request.headers.get('x-didit-signature', '')
    return hmac.compare_digest(f"sha256={expected}", received)

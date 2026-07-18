"""Cliente de Kushki — tarjetas Visa/MC internacionales.

Flujo: React tokeniza la tarjeta con Kushki.js (client-side) y envía el token.
Django cobra con el token. Nunca se manejan datos de tarjeta en el backend.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger('booking.payments')


def _url_base() -> str:
    return (
        'https://api.kushkipagos.com'
        if settings.KUSHKI_ENV == 'production'
        else 'https://api-uat.kushkipagos.com'
    )


def cobrar_con_token(kushki_token: str, monto_usd: str, reserva_id: int) -> dict:
    """Ejecuta el cobro con un token de Kushki. Devuelve la respuesta cruda."""
    response = requests.post(
        f"{_url_base()}/card/v1/charges",
        headers={
            'Private-Merchant-Id': settings.KUSHKI_PRIVATE_KEY,
            'Content-Type': 'application/json',
        },
        json={
            'token': kushki_token,
            'amount': {
                'subtotalIva': 0,
                'subtotalIva0': str(monto_usd),
                'iva': 0,
                'ice': 0,
                'currency': 'USD',
            },
            'metadata': {'reserva_id': str(reserva_id)},
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    logger.info('kushki.cobro.ejecutado', extra={'reserva_id': reserva_id})
    return data

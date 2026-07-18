"""Cliente de Floid — verificación de RUT contra el Registro Civil de Chile.

Solo aplica a usuarios con RUT chileno. Es complemento de Didit, NO bloqueante:
si Floid falla o no está configurado, la verificación visual de Didit basta.
"""

import logging

import requests
from django.conf import settings

logger = logging.getLogger('booking.kyc')


def verificar_rut_registro_civil(rut: str) -> dict:
    """
    Verifica un RUT chileno contra el Registro Civil.
    Devuelve {'valid': bool, ...}. Nunca lanza: los errores devuelven valid=True
    con flag de skip/timeout/error para no bloquear el flujo KYC.
    """
    if not settings.FLOID_API_KEY:
        logger.warning('floid.sin_api_key — verificación omitida')
        return {'valid': True, 'skip': True}

    try:
        response = requests.get(
            'https://api.floid.io/cl/registry/identity',
            headers={'Authorization': f'Bearer {settings.FLOID_API_KEY}'},
            params={'rut': _limpiar_rut(rut)},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()

        logger.info('floid.verificacion', extra={
            'rut_primeros': rut[:4] + '***',  # no loguear RUT completo
            'valid': data.get('valid'),
        })
        return data

    except requests.Timeout:
        logger.warning('floid.timeout — verificación omitida')
        return {'valid': True, 'timeout': True}
    except requests.RequestException as e:
        logger.error('floid.error', extra={'error': str(e)})
        return {'valid': True, 'error': str(e)}


def _limpiar_rut(rut: str) -> str:
    """Normalizar RUT: remover puntos y guión, uppercase K."""
    return rut.replace('.', '').replace('-', '').upper().strip()

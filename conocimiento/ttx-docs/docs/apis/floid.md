# Floid — Registro Civil Chile

**Qué hace:** Verifica RUT chileno contra el Registro Civil oficial. Complemento de Didit para usuarios con cédula chilena.
**Solo aplica a:** usuarios con RUT chileno. Usuarios de otros países → solo Didit.
**Docs:** https://floid.io

---

## ⚙️ CREDENCIALES REQUERIDAS

```
Antes de implementar esta sección, decirle a Gueremy:
"Necesito el API key de Floid para continuar."

□ FLOID_API_KEY
  → Obtener en: https://floid.io → Botón "Contactar" o registro directo
  → Precio: custom según volumen (no publicado)
  → Plan dev/sandbox disponible para pruebas
  → Tiempo de activación: 1-2 días hábiles
```

---

## Integración

```python
# booking/integrations/floid.py
import requests, logging
from django.conf import settings

logger = logging.getLogger('booking.kyc')


def verificar_rut_registro_civil(rut: str) -> dict:
    """
    Verifica un RUT chileno contra el Registro Civil.
    Solo se llama si el usuario es chileno (detectado por tipo de documento en Didit).

    Devuelve:
        {'valid': True, 'nombre': '...', 'vigente': True}
    O en error:
        {'valid': False, 'error': '...'}

    IMPORTANTE: Si Floid falla, no bloquear la verificación.
    Didit ya verificó la identidad visualmente. Floid es complemento, no bloqueante.
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
            'rut_primeros': rut[:4] + '***',  # No loguear RUT completo
            'valid': data.get('valid'),
        })
        return data

    except requests.Timeout:
        logger.warning('floid.timeout — verificación omitida')
        return {'valid': True, 'timeout': True}  # No bloquear por timeout
    except requests.RequestException as e:
        logger.error('floid.error', extra={'error': str(e)})
        return {'valid': True, 'error': str(e)}  # No bloquear por error de API


def _limpiar_rut(rut: str) -> str:
    """Normalizar RUT: remover puntos y guión, uppercase K."""
    return rut.replace('.', '').replace('-', '').upper().strip()
```

---

## Cuándo llamar a Floid

```python
def _es_usuario_chileno(perfil) -> bool:
    """
    Detectar si el usuario es chileno para decidir si llamar a Floid.
    Fuentes de información (por prioridad):
    1. El tipo de documento verificado por Didit (cédula chilena)
    2. El campo pais_documento en UserProfile (si existe)
    3. El RUT ingresado por el usuario (empieza con dígitos válidos)
    """
    # Simplificado para MVP: si tiene RUT en el perfil, es chileno
    return bool(getattr(perfil, 'rut', '').strip())
```

---

## Tests sin llamadas reales

```python
@pytest.fixture
def mock_floid(mocker):
    mock = mocker.patch('booking.integrations.floid.requests.get')
    mock.return_value.json.return_value = {
        'valid': True,
        'nombre': 'JUAN PEREZ GONZALEZ',
        'vigente': True,
    }
    mock.return_value.raise_for_status = lambda: None
    return mock
```

# Didit — KYC / AML / Wallet Screening

**Qué hace:** Verifica identidad (foto + selfie + liveness), screening AML y análisis de wallets crypto.
**Por qué Didit:** 500 verificaciones gratis/mes permanentes. $0.33/check. MCP server nativo para Claude Code.
**Docs:** https://docs.didit.me

---

## ⚙️ CREDENCIALES REQUERIDAS

```
Antes de implementar esta sección, decirle a Gueremy:
"Necesito las credenciales de Didit para continuar."

Variables a configurar en .env:

□ DIDIT_API_KEY
  → Obtener en: https://dashboard.didit.me
  → Ir a: Settings → API Keys → Create API Key
  → Copiar el valor completo

□ DIDIT_WEBHOOK_URL
  → Es tu URL pública: https://TU-DOMINIO/api/webhooks/didit/
  → En desarrollo local, usar ngrok: ngrok http 8000
  → La URL de ngrok cambia cada sesión — usar cuenta ngrok fija o serveo

□ DIDIT_WEBHOOK_SECRET
  → Se genera al crear el webhook en Didit dashboard
  → Ir a: Settings → Webhooks → Create Webhook
  → Pegar DIDIT_WEBHOOK_URL → copiar el secret generado

Free tier: 500 full KYC/mes sin tarjeta. Para testear: cuenta demo gratis.
Tiempo de setup desde cero: ~15 minutos.
```

---

## Pricing

| Feature | Precio | Free tier |
|---------|--------|-----------|
| ID Verification | $0.15/check | 500/mes |
| Passive Liveness | $0.10/check | 500/mes |
| Face Match 1:1 | $0.05/check | 500/mes |
| Device & IP Analysis | $0.03/check | 500/mes |
| **Full KYC bundle** | **$0.33/check** | **500/mes** |
| AML Screening | $0.20/check | — |
| Wallet Screening (KYT) | $0.15/check | — |

Solo se cobra por verificaciones **exitosas**. Fallos = $0.

---

## Integración completa

```python
# booking/integrations/didit.py
import hmac, hashlib, requests, logging
from django.conf import settings

logger = logging.getLogger('booking.kyc')


# ─── Crear sesión KYC ────────────────────────────────────────────────────────

def iniciar_sesion_kyc(user_id: int, tier_requerido: int) -> dict:
    """
    Crea sesión de verificación en Didit.
    Devuelve {'session_url': '...', 'session_id': '...'} para redirigir al usuario.
    """
    steps = _steps_para_tier(tier_requerido)

    try:
        response = requests.post(
            'https://api.didit.me/v3/session/',
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
            'user_id': user_id, 'session_id': data.get('session_id')
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


# ─── Wallet Screening ────────────────────────────────────────────────────────

def verificar_wallet(wallet_address: str) -> dict:
    """
    Verifica el riesgo de una wallet crypto antes de registrarla en ERC-3643.
    $0.15 por check. Devuelve {'risk_score': 0-100, 'flagged': bool}.
    """
    try:
        response = requests.post(
            'https://api.didit.me/v3/wallet-screening/',
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


# ─── Verificar firma del webhook ─────────────────────────────────────────────

def verificar_firma_webhook(request) -> bool:
    body = request.body
    expected = hmac.new(
        settings.DIDIT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    received = request.headers.get('x-didit-signature', '')
    return hmac.compare_digest(f"sha256={expected}", received)
```

---

## Webhook handler completo

```python
# booking/views/payments.py

from booking.integrations.didit import verificar_firma_webhook


class DiditWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        if not verificar_firma_webhook(request):
            logger.warning('didit.webhook.firma_invalida',
                           extra={'ip': request.META.get('REMOTE_ADDR')})
            return Response(status=403)

        data = request.data
        user_id = data.get('vendor_data')
        status = data.get('status')     # 'approved' | 'declined' | 'review' | 'expired'
        session_id = data.get('session_id')
        completed_steps = data.get('completed_steps', [])

        logger.info('didit.webhook.recibido', extra={
            'user_id': user_id, 'status': status, 'session_id': session_id
        })

        if status == 'approved':
            procesar_kyc_aprobado_task.delay(user_id, completed_steps)
        elif status == 'declined':
            procesar_kyc_rechazado_task.delay(user_id, data.get('decline_reasons', []))
        elif status == 'review':
            # Notificar a Joan para revisión manual (T4 Black o caso edge)
            notificar_revision_manual_kyc_task.delay(user_id, session_id)

        return Response(status=200)
```

---

## Tasks de Celery para KYC

```python
# booking/tasks.py

@shared_task
def procesar_kyc_aprobado_task(user_id: str, completed_steps: list):
    from .models import UserProfile, AuditLog
    from .constants import TIER_NOMBRES

    # Determinar tier según checks completados
    if 'aml_screening' in completed_steps:
        tier_nuevo = 3  # Gold
    else:
        tier_nuevo = 2  # Silver
    # T4 Black: requiere aprobación manual de Joan (no automático)

    perfil = UserProfile.objects.get(user_id=user_id)

    # Verificar RUT si es chileno
    if _es_usuario_chileno(perfil):
        from .integrations.floid import verificar_rut_chileno
        verificar_rut_chileno(perfil.rut, perfil.user)

    perfil.kyc_tier = tier_nuevo
    perfil.kyc_verificado_en = timezone.now()
    perfil.save(update_fields=['kyc_tier', 'kyc_verificado_en'])

    AuditLog.registrar(
        accion='kyc.aprobado',
        datos_despues={'tier': tier_nuevo, 'tier_nombre': TIER_NOMBRES[tier_nuevo]},
    )

    # Fase 3: registrar en Identity Registry ERC-3643
    if perfil.wallet_address:
        register_identity_task.delay(user_id)

    # Notificar al usuario
    from .integrations.resend import enviar_kyc_aprobado
    enviar_kyc_aprobado(perfil.user)
```

---

## Testing sin gastar créditos reales

```python
# tests/test_kyc.py
from unittest.mock import patch

@pytest.fixture
def mock_didit(mocker):
    """Mock completo de Didit para tests unitarios. No hace llamadas reales."""
    mock = mocker.patch('booking.integrations.didit.requests.post')
    mock.return_value.json.return_value = {
        'session_id': 'sess_test_123',
        'session_url': 'https://verify.didit.me/session/test',
        'status': 'created',
    }
    mock.return_value.raise_for_status = lambda: None
    return mock


def test_iniciar_kyc_crea_sesion(mock_didit, user_t1):
    result = iniciar_sesion_kyc(user_t1.id, tier_requerido=2)
    assert 'session_url' in result
    assert 'session_id' in result
    mock_didit.assert_called_once()


def test_webhook_firma_invalida_retorna_403(client, user_t1):
    response = client.post(
        '/api/webhooks/didit/',
        data={'vendor_data': str(user_t1.id), 'status': 'approved'},
        content_type='application/json',
        HTTP_X_DIDIT_SIGNATURE='sha256=invalida',
    )
    assert response.status_code == 403
    # El tier NO debe haber cambiado
    user_t1.userprofile.refresh_from_db()
    assert user_t1.userprofile.kyc_tier == 1
```

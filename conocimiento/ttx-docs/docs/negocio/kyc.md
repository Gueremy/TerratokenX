# KYC — TerraTokenX

## Los 4 niveles de verificación

| Tier | Nombre | Qué se verifica | API usada | Límite inversión |
|------|--------|-----------------|-----------|-----------------|
| 1 | Bronze | Email + teléfono | Django nativo | $1.000 USD |
| 2 | Silver | ID + Selfie + Liveness | Didit | $5.000 USD |
| 3 | Gold | ID + Selfie + AML | Didit + AML | $15.000 USD |
| 4 | Black VIP | EDD + revisión manual Joan | Didit + manual | $25.000 USD |

**Usuarios chilenos:** Didit hace el match foto-documento. Floid verifica el RUT contra el Registro Civil.
**Usuarios no chilenos:** Solo Didit. Soporta 220+ países, 14.000+ tipos de documento.

---

## KYC_LIMITS_USD (en constants.py)

```python
KYC_LIMITS_USD = {
    1: 1_000,    # Bronze — hasta $1.000 USD acumulado
    2: 5_000,    # Silver — hasta $5.000 USD
    3: 15_000,   # Gold   — hasta $15.000 USD
    4: 100_000,  # Black VIP — hasta $100.000 USD (límite operativo)
}
```

---

## KYCCheckMiddleware

```python
# booking/middleware.py
from decimal import Decimal
from django.http import JsonResponse
from .constants import KYC_LIMITS_USD
from .models import UserProfile


class KYCCheckMiddleware:
    """
    Se activa solo en endpoints de checkout (/api/comprar/, /api/creditos/comprar/).
    Bloquea si el usuario superaría su límite de inversión acumulada.
    NO bloquea endpoints de lectura (GET).
    """
    ENDPOINTS_PROTEGIDOS = [
        '/api/v1/comprar/',
        '/api/v1/creditos/comprar/',
    ]

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if (request.method == 'POST'
                and any(request.path.startswith(ep) for ep in self.ENDPOINTS_PROTEGIDOS)
                and request.user.is_authenticated):

            resultado = self._verificar_limite_kyc(request)
            if resultado is not None:
                return resultado

        return self.get_response(request)

    def _verificar_limite_kyc(self, request) -> JsonResponse | None:
        try:
            perfil = request.user.userprofile
        except UserProfile.DoesNotExist:
            return JsonResponse(
                {'error': 'Perfil de usuario no encontrado'},
                status=400
            )

        limite = Decimal(str(KYC_LIMITS_USD.get(perfil.kyc_tier, 1000)))

        if perfil.investment_total_usd >= limite:
            return JsonResponse(
                {
                    'error': 'limite_kyc_superado',
                    'message': (
                        f'Has alcanzado el límite de inversión para tu nivel '
                        f'({perfil.get_tier_display()}). '
                        f'Completa la verificación de identidad para subir de nivel.'
                    ),
                    'tier_actual': perfil.kyc_tier,
                    'limite_usd': str(limite),
                    'acumulado_usd': str(perfil.investment_total_usd),
                },
                status=403
            )
        return None
```

Registrar el middleware en `settings/base.py`:
```python
MIDDLEWARE = [
    ...
    'booking.middleware.KYCCheckMiddleware',
]
```

---

## Flujo de verificación con Didit

```
Usuario quiere subir a T2+ (Silver/Gold/Black)
    ↓
Frontend: botón "Verificar identidad"
    ↓
Backend: POST /api/v1/kyc/iniciar/ → crear sesión en Didit
    ↓
Backend devuelve: {"session_url": "https://verify.didit.me/session/..."}
    ↓
Frontend: redirige al usuario a session_url
    ↓
Usuario: sube cédula/pasaporte + hace selfie en Didit (UI de Didit)
    ↓
Didit: procesa (< 30 segundos)
    ↓
Didit: POST webhook a /api/webhooks/didit/ con resultado
    ↓
Backend: verifica firma → actualiza kyc_tier en UserProfile
    ↓
Si tiene wallet: registra en Identity Registry ERC-3643 (Fase 3)
```

---

## Lógica chilenos vs no chilenos

```python
# booking/integrations/didit.py

def iniciar_verificacion_kyc(user, tier_requerido: int) -> dict:
    """
    Crea una sesión de verificación KYC en Didit.
    Devuelve la URL para redirigir al usuario.
    """
    steps = _get_steps_para_tier(tier_requerido)

    response = requests.post(
        'https://api.didit.me/v3/session/',
        headers={'Authorization': f'Bearer {settings.DIDIT_API_KEY}'},
        json={
            'vendor_data': str(user.id),
            'callback': settings.DIDIT_WEBHOOK_URL,
            'steps': steps,
        },
        timeout=10,
    )
    response.raise_for_status()
    data = response.json()

    # Guardar el session_id para correlacionar con el webhook
    UserProfile.objects.filter(user=user).update(
        didit_session_id=data['session_id']
    )

    return {'session_url': data['session_url']}


def _get_steps_para_tier(tier: int) -> list:
    base = ['id_verification', 'passive_liveness', 'face_match']
    if tier >= 3:
        base.append('aml_screening')
    return base
```

```python
# Para usuarios chilenos — verificación adicional contra Registro Civil
def verificar_rut_chileno(rut: str, user) -> bool:
    """
    Solo para usuarios con RUT chileno (detected por documento Didit).
    Usa Floid para validar contra Registro Civil oficial.
    """
    if not settings.FLOID_API_KEY:
        return True  # Si no hay Floid configurado, omitir el check

    try:
        response = requests.get(
            'https://api.floid.io/cl/registry/identity',
            headers={'Authorization': f'Bearer {settings.FLOID_API_KEY}'},
            params={'rut': rut},
            timeout=5,
        )
        response.raise_for_status()
        data = response.json()
        return data.get('valid', False)
    except Exception:
        # Si Floid falla, no bloquear la verificación
        # (Didit ya verificó la identidad visualmente)
        return True
```

---

## Webhook handler de Didit

```python
# booking/views/payments.py

from django.views.decorators.csrf import csrf_exempt
from django.utils.decorators import method_decorator


@method_decorator(csrf_exempt, name='dispatch')
class DiditWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        # 1. Verificar firma
        if not verificar_firma_didit(request):
            return Response({'error': 'Firma inválida'}, status=403)

        data = request.data
        user_id = data.get('vendor_data')
        status = data.get('status')  # 'approved' | 'declined' | 'review'
        session_id = data.get('session_id')

        if status == 'approved':
            _procesar_kyc_aprobado(user_id, data)
        elif status == 'declined':
            _procesar_kyc_rechazado(user_id, data)
        # 'review' → notificar a Joan para revisión manual

        return Response(status=200)


def _procesar_kyc_aprobado(user_id: str, data: dict) -> None:
    from .models import UserProfile, AuditLog
    from .tasks import register_identity_blockchain_task

    tier_nuevo = _determinar_nuevo_tier(data)

    UserProfile.objects.filter(user_id=user_id).update(
        kyc_tier=tier_nuevo,
        kyc_verificado_en=timezone.now(),
    )

    AuditLog.registrar(
        accion='kyc.aprobado',
        datos_despues={
            'tier_nuevo': tier_nuevo,
            'provider': 'didit',
            'session_id': data.get('session_id'),
        },
    )

    # Fase 3: registrar wallet en Identity Registry ERC-3643
    perfil = UserProfile.objects.get(user_id=user_id)
    if perfil.wallet_address:
        register_identity_blockchain_task.delay(user_id)


def _determinar_nuevo_tier(data: dict) -> int:
    """
    Determina el tier basado en los checks completados por Didit.
    Si pasó AML → T3. Si solo hizo ID+selfie → T2.
    """
    checks = data.get('completed_steps', [])
    if 'aml_screening' in checks:
        return 3  # Gold
    return 2  # Silver
    # T4 Black → requiere aprobación manual de Joan
```

---

## Criterios de aceptación (Semana 3)

```
✅ PASS si:
  - Middleware bloquea POST /api/v1/comprar/ para T1 con investment_total_usd >= 1000
  - Middleware NO bloquea GET requests
  - Middleware NO bloquea usuarios con kyc_tier=4
  - Webhook Didit con firma válida + status=approved → kyc_tier actualizado en DB
  - Webhook Didit con firma inválida → 403 (sin cambios en DB)
  - Usuario chileno → se llama a Floid (con mock en tests)
  - Usuario no chileno → no se llama a Floid

❌ FAIL si:
  - Middleware usa float para comparar montos
  - Webhook procesa sin verificar firma
  - El tier se hardcodea en vez de calcularse desde los steps de Didit
```

# Pasarelas de Pago — TerraTokenX

## Los tres métodos

| Pasarela | Usa para | Fee | Webhook |
|----------|----------|-----|---------|
| MercadoPago | Pesos chilenos, tarjetas locales | ~3.49% | HMAC-SHA256 |
| Cryptomus | Crypto global (+100 monedas) | 0.4% | MD5 + IP |
| Kushki | Visa/MC internacionales | Negociado | JWT/HMAC |

**Regla de idempotencia:** Si el payment_id ya existe en DB con estado CONFIRMADO, devolver 200 sin procesar. Nunca procesar el mismo pago dos veces.

---

## MercadoPago

### Crear preferencia de pago

```python
# booking/integrations/mercadopago_client.py
import mercadopago


def crear_preferencia_mp(reserva) -> dict:
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    preference_data = {
        "items": [{
            "title": f"Tokens {reserva.proyecto.nombre}",
            "quantity": reserva.cantidad_tokens,
            "unit_price": float(reserva.total / reserva.cantidad_tokens),
            "currency_id": "CLP",
        }],
        "external_reference": str(reserva.id),
        "notification_url": f"{settings.BASE_URL}/api/webhooks/mp/",
        "back_urls": {
            "success": f"{settings.FRONTEND_URL}/compra/exito/",
            "failure": f"{settings.FRONTEND_URL}/compra/error/",
            "pending": f"{settings.FRONTEND_URL}/compra/pendiente/",
        },
        "auto_return": "approved",
    }

    result = sdk.preference().create(preference_data)
    return result["response"]
```

### Webhook handler

```python
# booking/views/payments.py
import hmac, hashlib

def verificar_firma_mp(request) -> bool:
    ts = request.headers.get('x-request-id', '')
    data_id = request.data.get('data', {}).get('id', '')
    manifest = f"id:{data_id};request-id:{ts};"
    expected = hmac.new(
        settings.MERCADOPAGO_WEBHOOK_SECRET.encode(),
        manifest.encode(),
        hashlib.sha256
    ).hexdigest()
    received = request.headers.get('x-signature', '')
    # x-signature tiene formato: "ts=...,v1=HASH"
    v1 = dict(part.split('=', 1) for part in received.split(',') if '=' in part).get('v1', '')
    return hmac.compare_digest(expected, v1)


class MPWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        if not verificar_firma_mp(request):
            return Response(status=403)

        topic = request.data.get('type')
        if topic != 'payment':
            return Response(status=200)

        payment_id = str(request.data.get('data', {}).get('id', ''))
        procesar_pago_mp_task.delay(payment_id)
        return Response(status=200)
```

```python
# booking/tasks.py
@shared_task(bind=True, max_retries=3)
def procesar_pago_mp_task(self, payment_id: str):
    import mercadopago
    sdk = mercadopago.SDK(settings.MERCADOPAGO_ACCESS_TOKEN)

    try:
        payment = sdk.payment().get(payment_id)
        data = payment['response']
        status = data.get('status')

        if status != 'approved':
            return

        reserva_id = int(data.get('external_reference', 0))

        # Idempotencia
        reserva = Reserva.objects.filter(id=reserva_id).first()
        if not reserva or reserva.estado_pago == EstadoPago.CONFIRMADO:
            return

        reserva.mp_payment_id = payment_id
        reserva.save(update_fields=['mp_payment_id'])
        confirmar_reserva(reserva_id)

    except Exception as exc:
        raise self.retry(exc=exc, countdown=60)
```

---

## Cryptomus

### Todos los statuses del webhook

| Status | Significado | Acción en Django |
|--------|-------------|------------------|
| `paid` | Pago exacto recibido | ✅ Confirmar Reserva |
| `paid_over` | Pagaron de más | ✅ Confirmar + registrar excedente en AuditLog |
| `wrong_amount` | Pagaron de menos | ❌ Marcar FALLIDO, liberar stock, notificar |
| `cancel` | Usuario canceló | ❌ Liberar stock del Drop |
| `fail` / `system_fail` | Fallo técnico | ❌ Retry automático, notificar |
| `check` | Revisión manual | ⏳ Alerta a Joan |
| `process` | En proceso | 🔄 No hacer nada, esperar siguiente webhook |
| `refund_paid` | Devolución completada | 📋 Registrar en CreditTransaction tipo DEVOLUCION |

### Crear invoice

```python
# booking/integrations/cryptomus.py
import hashlib, base64, json, requests


def crear_invoice_cryptomus(reserva) -> dict:
    """Devuelve la URL de pago para redirigir al usuario."""
    payload = {
        'amount': str(reserva.total),
        'currency': 'USD',
        'order_id': str(reserva.id),
        'url_callback': f"{settings.BASE_URL}/api/webhooks/cryptomus/",
        'url_success': f"{settings.FRONTEND_URL}/compra/exito/",
        'url_return': f"{settings.FRONTEND_URL}/compra/",
        'is_payment_multiple': False,
        'lifetime': 3600,  # 1 hora para pagar
    }

    sign = _generar_firma_cryptomus(payload)

    response = requests.post(
        'https://api.cryptomus.com/v1/payment',
        json=payload,
        headers={
            'merchant': settings.CRYPTOMUS_MERCHANT_ID,
            'sign': sign,
            'Content-Type': 'application/json',
        },
        timeout=15,
    )
    response.raise_for_status()
    data = response.json()
    return data['result']


def _generar_firma_cryptomus(payload: dict) -> str:
    body_json = json.dumps(payload, separators=(',', ':'))
    body_b64 = base64.b64encode(body_json.encode()).decode()
    sign = hashlib.md5(
        f"{body_b64}{settings.CRYPTOMUS_PAYMENT_API_KEY}".encode()
    ).hexdigest()
    return sign


def verificar_firma_webhook_cryptomus(request) -> bool:
    """Verificar firma del webhook entrante de Cryptomus."""
    data = request.data.copy()
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
```

### Webhook handler

```python
class CryptomussWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        if not verificar_firma_webhook_cryptomus(request):
            return Response(status=403)

        data = request.data
        status = data.get('status')
        uuid = data.get('uuid')
        order_id = data.get('order_id')
        is_final = data.get('is_final', False)

        if not is_final:
            return Response(status=200)  # Aún en proceso

        if status == 'paid':
            procesar_pago_confirmado_crypto_task.delay(order_id, uuid)

        elif status == 'paid_over':
            procesar_pago_confirmado_crypto_task.delay(order_id, uuid)
            # AuditLog del excedente — manejado dentro del task

        elif status in ('wrong_amount', 'cancel', 'fail', 'system_fail'):
            procesar_pago_fallido_crypto_task.delay(order_id, status)

        elif status == 'check':
            notificar_revision_manual_task.delay(order_id)

        return Response(status=200)
```

---

## Kushki

### Flujo de tokenización

```
React: Kushki.js tokeniza la tarjeta del usuario (client-side)
    ↓ Devuelve: kushki_token (nunca los datos de tarjeta)
    ↓
React: envía kushki_token al backend
    ↓
Django: cobra con el token via Kushki API
    ↓
Kushki: webhook de confirmación
```

```python
# booking/integrations/kushki.py
import requests


def cobrar_con_kushki(reserva, kushki_token: str) -> dict:
    url_base = (
        'https://api.kushkipagos.com'
        if settings.KUSHKI_ENV == 'production'
        else 'https://api-uat.kushkipagos.com'
    )

    response = requests.post(
        f"{url_base}/v1/charges",
        headers={
            'Private-Merchant-Id': settings.KUSHKI_PRIVATE_KEY,
            'Content-Type': 'application/json',
        },
        json={
            'token': kushki_token,
            'amount': {
                'subtotalIva': 0,
                'subtotalIva0': float(reserva.total),
                'iva': 0,
                'ice': 0,
                'currency': 'USD',
            },
            'metadata': {'reserva_id': str(reserva.id)},
        },
        timeout=15,
    )
    response.raise_for_status()
    return response.json()
```

---

## Patrón común a las 3 pasarelas

```python
# Cada webhook debe seguir este patrón exacto:

def webhook_handler(request):
    # 1. VERIFICAR FIRMA — siempre primero
    if not verificar_firma(request):
        return Response(status=403)

    # 2. EXTRAER IDENTIFICADOR ÚNICO
    payment_ref = extraer_id_unico(request.data)

    # 3. IDEMPOTENCIA — ¿ya lo procesamos?
    if ya_fue_procesado(payment_ref):
        return Response(status=200)  # OK silencioso

    # 4. DELEGAR A CELERY — nunca procesar en el webhook directamente
    procesar_pago_task.delay(payment_ref)

    # 5. RESPONDER 200 INMEDIATAMENTE
    return Response(status=200)
```

---

## URL del webhook — registrar en urls.py

```python
# booking/urls.py
urlpatterns = [
    ...
    path('api/webhooks/mp/',          MPWebhookView.as_view(),         name='webhook-mp'),
    path('api/webhooks/cryptomus/',   CryptomussWebhookView.as_view(), name='webhook-cryptomus'),
    path('api/webhooks/kushki/',      KushkiWebhookView.as_view(),     name='webhook-kushki'),
    path('api/webhooks/didit/',       DiditWebhookView.as_view(),      name='webhook-didit'),
]
```

---

## Criterios de aceptación — Semana 5 (Cryptomus)

```
✅ PASS si:
  - POST /api/webhooks/cryptomus/ con firma válida + status=paid → Reserva CONFIRMADO
  - POST /api/webhooks/cryptomus/ con firma inválida → 403, sin cambios
  - Segundo POST con mismo uuid → 200 sin cambios (idempotencia)
  - status=wrong_amount → Reserva FALLIDO + stock devuelto al Drop
  - status=cancel → stock devuelto al Drop
  - is_final=false → 200 sin procesar (aún en proceso)

❌ FAIL si:
  - Webhook procesa sin verificar firma
  - Mismo uuid procesado dos veces
  - Stock no se devuelve en caso de fallo/cancelación
```

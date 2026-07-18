# Arquitectura — TerraTokenX Backend

## La regla más importante

**La lógica de negocio vive en `services.py`. Nunca en views.**

Si una view tiene más de 10 líneas de lógica, algo está mal.
Si hay un `if` de negocio en una view, moverlo a services.

---

## Las capas del sistema

```
HTTP Request
     ↓
  View / APIView          ← recibe input, valida serializer, devuelve response
     ↓
  Service Layer           ← TODA la lógica de negocio aquí
     ↓
  Selector Layer          ← TODAS las queries a la DB aquí
     ↓
  Models / ORM            ← solo estructura de datos
     ↓
  PostgreSQL
```

**View** → no piensa, solo traduce HTTP a Python y Python a HTTP.
**Service** → sabe qué hacer (confirmar una reserva, aplicar un crédito).
**Selector** → sabe cómo buscar datos (proyectos activos con drop activo).
**Model** → sabe cómo es la estructura (campos, relaciones, validaciones básicas).

---

## Estructura de carpetas (post-refactorización)

```
terratokenx-backend/
│
├── CLAUDE.md
├── .env
├── .env.example
├── manage.py
├── requirements.txt
├── docs/
│
├── terratokenx/                ← proyecto Django
│   ├── settings/
│   │   ├── base.py             ← config compartida
│   │   ├── local.py            ← desarrollo (DEBUG=True, email console)
│   │   └── production.py       ← Render (DEBUG=False, logging JSON)
│   ├── urls.py
│   ├── wsgi.py
│   └── asgi.py
│
└── booking/                    ← app principal
    ├── models.py               ← modelos existentes
    ├── models/                 ← [crear] módulos por dominio
    │   ├── __init__.py
    │   ├── creditos.py         ← CreditBalance, CreditTransaction
    │   └── fees.py             ← TierConfig, FeeConfig
    ├── constants.py            ← EstadoPago, MetodoPago, KYCLimites, TIER_NOMBRES
    ├── exceptions.py           ← [crear] excepciones propias
    ├── services.py             ← [crear] lógica de negocio
    ├── selectors.py            ← [crear] queries reutilizables
    ├── serializers.py          ← [crear] serializers DRF
    ├── middleware.py           ← [crear] KYCCheckMiddleware
    ├── tasks.py                ← [crear] Celery tasks
    ├── signals.py              ← signals existentes (UserProfile)
    ├── admin.py
    ├── urls.py
    ├── migrations/
    ├── views/                  ← paquete con 7 módulos (ya refactorizado)
    │   ├── __init__.py
    │   ├── public.py
    │   ├── payments.py
    │   ├── api.py              ← endpoints REST para React
    │   ├── admin_views.py
    │   ├── investor.py
    │   ├── fractionalizer.py
    │   └── utils.py
    ├── integrations/           ← [crear] clients de APIs externas
    │   ├── __init__.py
    │   ├── cryptomus.py
    │   ├── kushki.py
    │   ├── didit.py
    │   ├── floid.py
    │   └── resend.py
    └── abis/                   ← [crear en Fase 3] ABIs de contratos ERC-3643
        ├── token.json
        ├── identity_registry.json
        ├── compliance.json
        └── factory.json
```

---

## Cómo se ve un flujo correcto

**Confirmar una reserva (el ejemplo canónico):**

```python
# ✅ CORRECTO

# views/payments.py — solo orquesta
class MercadoPagoWebhookView(APIView):
    permission_classes = []

    def post(self, request):
        if not verificar_firma_mp(request):          # delegado a utils
            return Response(status=403)

        payment_id = request.data.get('data', {}).get('id')
        confirmar_reserva_por_pago_mp.delay(payment_id)  # delegado a Celery
        return Response(status=200)


# services.py — aquí vive la lógica
@transaction.atomic
def confirmar_reserva(reserva_id: int) -> Reserva:
    reserva = Reserva.objects.select_for_update().get(id=reserva_id)

    if reserva.estado_pago == EstadoPago.CONFIRMADO:
        raise IdempotenciaError(f"Reserva {reserva_id} ya confirmada")

    reserva.estado_pago = EstadoPago.CONFIRMADO
    reserva.save()

    _aplicar_fee_transaccion(reserva)
    AuditLog.registrar(accion='reserva.confirmada', objeto=reserva)
    enviar_email_confirmacion.delay(reserva_id)      # Celery async
    return reserva


# selectors.py — aquí viven las queries
def get_reserva_por_payment_id(payment_id: str) -> Reserva | None:
    return Reserva.objects.select_related(
        'user__userprofile', 'proyecto'
    ).filter(mp_payment_id=payment_id).first()
```

```python
# ❌ INCORRECTO — lógica de negocio en la view

class MercadoPagoWebhookView(APIView):
    def post(self, request):
        payment_id = request.data.get('data', {}).get('id')
        reserva = Reserva.objects.get(mp_payment_id=payment_id)  # ← query en view
        reserva.estado_pago = 'CONFIRMADO'                        # ← lógica en view
        reserva.save()
        send_mail(...)                                             # ← email en view
        return Response(status=200)
```

---

## Reglas de arquitectura

1. Las views **no** importan modelos directamente para hacer queries — usan selectors.
2. Los services **no** conocen HTTP — no usan `request`, `response`, ni status codes.
3. Los selectors **no** contienen lógica de negocio — solo construyen querysets.
4. Las integraciones (`booking/integrations/`) **no** conocen modelos de Django — devuelven datos puros.
5. Las tasks de Celery **son** thin wrappers de services — llaman un service y manejan el retry.

---

## Nomenclatura

```python
# Services — verbos de negocio
confirmar_reserva(reserva_id)
aplicar_credito(user_id, monto, reserva_id)
calcular_fee(monto_usd, tipo, tier)
crear_drop(proyecto_id, datos)

# Selectors — sustantivos con get_ o list_
get_drop_activo(proyecto_id)
get_balance_creditos(user_id)
list_reservas_usuario(user_id)
list_proyectos_activos()

# Exceptions — PascalCase, descriptivos
class DropInactivo(Exception): pass
class StockInsuficiente(Exception): pass
class LimiteKYCSuperado(Exception): pass
class CreditoInsuficiente(Exception): pass
class IdempotenciaError(Exception): pass
class BlockchainTransactionFailed(Exception): pass
```

# Créditos RWA y Tiers — TerraTokenX

## Reglas de negocio — NO negociables

1. Créditos expiran **exactamente 12 meses** desde la emisión.
2. Extensión: **una sola vez por usuario**, sube a 18 meses.
3. Los créditos **NO son reembolsables** en efectivo.
4. Los créditos **NO son transferibles** entre usuarios.
5. Fees se calculan **ANTES** de aplicar créditos.
6. Los créditos se libera en 3 Drops: **30% / 30% / 40%**.
7. **NUNCA** usar lenguaje de rentabilidad/inversión en código, emails o mensajes.

---

## Los 4 Tiers

| Tier | Nombre | Cap créditos | Descuento fees | Descuento créditos | KYC |
|------|--------|-------------|----------------|--------------------|-----|
| 1 | Bronze | $1.000 USD | 7.5% | 10% (paga $900 por $1.000) | lite |
| 2 | Silver | $5.000 USD | 15% | 20% (paga $800 por $1.000) | standard |
| 3 | Gold | $15.000 USD | 22.5% | 30% (paga $700 por $1.000) | standard |
| 4 | Black VIP | $25.000 USD | 31.5% | 40% (paga $600 por $1.000) | edd |

El descuento de créditos se aplica al COMPRAR créditos, no al usarlos.

---

## Fee Schedule

| Tipo | Porcentaje | Mínimo USD |
|------|-----------|------------|
| Listing/Originación | 1.5% | $500 |
| Transacción (comprador) | 1.0% | $0 |
| Transacción (vendedor) | 1.0% | $0 |
| Administración anual | 1.0% | $0 (prorrateado) |
| Cash-out/Retiro | 1.0% | $0 |
| Servicios premium | 0% | $10 a $500 |

Los tiers aplican descuento sobre el fee. El descuento es el `descuento_fees_pct`.

---

## calcular_fee() — SIEMPRE con Decimal

```python
# booking/services_creditos.py
from decimal import Decimal, ROUND_HALF_UP
from .models import FeeConfig, TierConfig


def calcular_fee(
    monto_usd: Decimal,
    tipo_fee: str,
    tier_usuario: int,
) -> Decimal:
    """
    Calcula el fee final después del descuento por tier.
    Siempre devuelve Decimal con 2 decimales.
    NUNCA usa float.
    """
    fee_cfg   = FeeConfig.objects.get(tipo=tipo_fee, activo=True)
    tier_cfg  = TierConfig.objects.get(tier=tier_usuario)

    # Fee base
    fee_base = (monto_usd * fee_cfg.porcentaje / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    fee_base = max(fee_base, fee_cfg.monto_minimo_usd)

    # Descuento por tier
    descuento = (fee_base * tier_cfg.descuento_fees_pct / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    fee_final = (fee_base - descuento).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    return fee_final


def calcular_precio_creditos(
    monto_usd: Decimal,
    tier_usuario: int,
) -> Decimal:
    """
    Cuánto paga el usuario por $monto_usd en créditos, según su tier.
    T1: paga $900 por $1.000 en créditos (10% off)
    T4: paga $600 por $1.000 en créditos (40% off)
    """
    tier_cfg = TierConfig.objects.get(tier=tier_usuario)
    descuento_pct = tier_cfg.descuento_creditos_pct
    precio = monto_usd * (Decimal('100') - descuento_pct) / Decimal('100')
    return precio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)
```

---

## comprar_creditos() service

```python
from django.db import transaction
from django.utils import timezone
from datetime import timedelta


@transaction.atomic
def comprar_creditos(
    user,
    monto_creditos_usd: Decimal,
    metodo_pago: str,
) -> dict:
    """
    Registra la intención de compra de créditos.
    Los créditos se acreditan DESPUÉS de confirmar el pago via webhook.
    Devuelve el precio que el usuario debe pagar.
    """
    tier = user.userprofile.kyc_tier
    tier_cfg = TierConfig.objects.get(tier=tier)

    # Verificar cap de créditos del tier
    balance, _ = CreditBalance.objects.get_or_create(
        user=user,
        defaults={
            'balance_usd': Decimal('0.00'),
            'tier': tier,
            'expires_at': timezone.now() + timedelta(days=365),
        }
    )

    if balance.balance_usd + monto_creditos_usd > tier_cfg.cap_creditos_usd:
        raise LimiteKYCSuperado(
            f"Superarías el cap de ${tier_cfg.cap_creditos_usd} USD para tier {tier}"
        )

    precio_a_pagar = calcular_precio_creditos(monto_creditos_usd, tier)

    return {
        'monto_creditos': monto_creditos_usd,
        'precio_a_pagar': precio_a_pagar,
        'descuento_aplicado': monto_creditos_usd - precio_a_pagar,
        'tier': tier,
    }


@transaction.atomic
def acreditar_creditos(user, monto_creditos_usd: Decimal, descripcion: str) -> None:
    """
    Acredita créditos al usuario DESPUÉS de confirmar pago.
    Llamado desde webhook de confirmación.
    """
    balance = CreditBalance.objects.select_for_update().get(user=user)
    balance.balance_usd += monto_creditos_usd
    balance.save(update_fields=['balance_usd'])

    CreditTransaction.objects.create(
        user=user,
        tipo='COMPRA',
        monto_usd=monto_creditos_usd,
        descripcion=descripcion,
    )
```

---

## aplicar_credito() — En el checkout

```python
@transaction.atomic
def aplicar_credito_en_checkout(
    user,
    monto_a_aplicar: Decimal,
    reserva,
) -> Decimal:
    """
    Descuenta créditos del balance para una compra.
    Devuelve el monto efectivamente descontado.
    Los fees ya deben estar calculados ANTES de llamar esta función.
    """
    if monto_a_aplicar <= 0:
        return Decimal('0.00')

    balance = CreditBalance.objects.select_for_update().get(user=user)

    # No aplicar más de lo disponible
    a_descontar = min(monto_a_aplicar, balance.balance_usd)

    balance.balance_usd -= a_descontar
    balance.save(update_fields=['balance_usd'])

    CreditTransaction.objects.create(
        user=user,
        tipo='USO',
        monto_usd=a_descontar,
        reserva=reserva,
        descripcion=f'Créditos aplicados en compra de {reserva.cantidad_tokens} tokens',
    )

    return a_descontar
```

---

## Expiración automática (Celery task — Semana 4)

```python
# booking/tasks.py
from celery import shared_task
from django.utils import timezone
from django.db import transaction


@shared_task
def expirar_creditos_vencidos():
    """
    Corre diariamente a las 2 AM (América/Santiago).
    Expira créditos de usuarios cuyo expires_at ya pasó.
    """
    vencidos = CreditBalance.objects.filter(
        expires_at__lt=timezone.now(),
        balance_usd__gt=0,
    ).select_for_update()

    with transaction.atomic():
        count = 0
        for balance in vencidos:
            monto_expirado = balance.balance_usd
            CreditTransaction.objects.create(
                user=balance.user,
                tipo='EXPIRACION',
                monto_usd=monto_expirado,
                descripcion='Créditos expirados automáticamente',
            )
            balance.balance_usd = Decimal('0.00')
            balance.save(update_fields=['balance_usd'])
            count += 1

    return f"Créditos expirados para {count} usuarios"
```

Beat schedule (en `settings/base.py`):
```python
from celery.schedules import crontab

CELERY_BEAT_SCHEDULE = {
    'expirar-creditos-diario': {
        'task': 'booking.tasks.expirar_creditos_vencidos',
        'schedule': crontab(hour=2, minute=0),  # 2 AM Chile
    },
}
```

---

## Claims permitidos y prohibidos

### ✅ PERMITIDO escribir en código, emails, UI:

```python
"Créditos para compras futuras dentro de TerraTokenX"
"Acceso preferente según tu Tier"
"Ventana limitada: stock por tramos"
"Descuento de X% al comprar créditos con tu tier"
"Créditos disponibles hasta [fecha]"
```

### ❌ PROHIBIDO — si aparece esto en código o mensajes, es un bug:

```python
"rentabilidad"     # ← NUNCA
"dividendo"        # ← NUNCA
"retorno"          # ← NUNCA en contexto financiero
"garantizado"      # ← NUNCA junto a dinero o créditos
"plusvalía"        # ← NUNCA
"respaldo directo por tierras"  # ← NUNCA
```

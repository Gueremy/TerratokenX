"""Services de créditos RWA y fee schedule.

Reglas de negocio (docs/negocio/creditos-tiers.md):
- Créditos expiran exactamente 12 meses desde la emisión (extensión única a 18m).
- No son reembolsables ni transferibles.
- Los fees se calculan ANTES de aplicar créditos.
- Todo cálculo de dinero usa Decimal. NUNCA float.
"""

import logging
from datetime import timedelta
from decimal import ROUND_HALF_UP, Decimal

from django.db import transaction
from django.utils import timezone

from .exceptions import CreditoInsuficiente, IdempotenciaError, LimiteKYCSuperado
from .models import CreditBalance, CreditTransaction, TierConfig

logger = logging.getLogger('booking')


def calcular_fee(monto_usd: Decimal, tipo_fee: str, tier_usuario: int) -> Decimal:
    """
    Calcula el fee final después del descuento por tier.
    Siempre devuelve Decimal con 2 decimales.
    """
    from .models import FeeConfig

    fee_cfg = FeeConfig.objects.get(tipo=tipo_fee, activo=True)
    tier_cfg = TierConfig.objects.get(tier=tier_usuario)

    # Fee base
    fee_base = (monto_usd * fee_cfg.porcentaje / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )
    fee_base = max(fee_base, fee_cfg.monto_minimo_usd)

    # Descuento por tier
    descuento = (fee_base * tier_cfg.descuento_fees_pct / Decimal('100')).quantize(
        Decimal('0.01'), rounding=ROUND_HALF_UP
    )

    return (fee_base - descuento).quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


def calcular_precio_creditos(monto_usd: Decimal, tier_usuario: int) -> Decimal:
    """
    Cuánto paga el usuario por $monto_usd en créditos, según su tier.
    T1: paga $900 por $1.000 en créditos (10% off)
    T4: paga $600 por $1.000 en créditos (40% off)
    """
    tier_cfg = TierConfig.objects.get(tier=tier_usuario)
    precio = monto_usd * (Decimal('100') - tier_cfg.descuento_creditos_pct) / Decimal('100')
    return precio.quantize(Decimal('0.01'), rounding=ROUND_HALF_UP)


@transaction.atomic
def comprar_creditos(user, monto_creditos_usd: Decimal, metodo_pago: str) -> dict:
    """
    Registra la intención de compra de créditos.
    Los créditos se acreditan DESPUÉS de confirmar el pago vía webhook.
    Devuelve el precio que el usuario debe pagar.
    """
    from .models import UserProfile

    perfil, _ = UserProfile.objects.get_or_create(user=user)
    tier = perfil.kyc_tier
    tier_cfg = TierConfig.objects.get(tier=tier)

    balance, _ = CreditBalance.objects.get_or_create(
        user=user,
        defaults={
            'balance_usd': Decimal('0.00'),
            'tier': tier,
            'expires_at': timezone.now() + timedelta(days=365),
        },
    )

    if balance.balance_usd + monto_creditos_usd > tier_cfg.cap_creditos_usd:
        raise LimiteKYCSuperado(
            f"Superarías el cap de ${tier_cfg.cap_creditos_usd} USD en créditos para tier {tier}"
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
    Acredita créditos al usuario DESPUÉS de confirmar el pago.
    Llamado desde el webhook de confirmación.
    """
    balance, _ = CreditBalance.objects.select_for_update().get_or_create(
        user=user,
        defaults={
            'balance_usd': Decimal('0.00'),
            'tier': getattr(getattr(user, 'profile', None), 'kyc_tier', 1),
            'expires_at': timezone.now() + timedelta(days=365),
        },
    )
    balance.balance_usd += monto_creditos_usd
    balance.save(update_fields=['balance_usd'])

    CreditTransaction.objects.create(
        user=user,
        tipo='COMPRA',
        monto_usd=monto_creditos_usd,
        descripcion=descripcion,
    )
    logger.info("Créditos acreditados a %s: $%s", user.email, monto_creditos_usd)


@transaction.atomic
def aplicar_credito_en_checkout(user, monto_a_aplicar: Decimal, reserva=None) -> Decimal:
    """
    Descuenta créditos del balance para una compra.
    Devuelve el monto efectivamente descontado.
    Los fees ya deben estar calculados ANTES de llamar esta función.
    Lanza CreditoInsuficiente si el saldo no alcanza.
    """
    if monto_a_aplicar <= 0:
        return Decimal('0.00')

    try:
        balance = CreditBalance.objects.select_for_update().get(user=user)
    except CreditBalance.DoesNotExist:
        raise CreditoInsuficiente("No tienes créditos disponibles")

    if balance.expires_at < timezone.now():
        raise CreditoInsuficiente("Tus créditos están vencidos")

    if monto_a_aplicar > balance.balance_usd:
        raise CreditoInsuficiente(f"Saldo disponible: ${balance.balance_usd}")

    balance.balance_usd -= monto_a_aplicar
    balance.save(update_fields=['balance_usd'])

    CreditTransaction.objects.create(
        user=user,
        tipo='USO',
        monto_usd=monto_a_aplicar,
        reserva=reserva,
        descripcion=(
            f'Créditos aplicados en compra de {reserva.cantidad_tokens} tokens'
            if reserva else 'Créditos aplicados en checkout'
        ),
    )
    return monto_a_aplicar


@transaction.atomic
def extender_expiracion_creditos(user) -> CreditBalance:
    """
    Extiende la expiración de créditos a 18 meses desde la emisión.
    Solo una vez por usuario.
    """
    balance = CreditBalance.objects.select_for_update().get(user=user)
    if balance.extended:
        raise IdempotenciaError("La extensión ya fue utilizada")

    balance.expires_at = balance.expires_at + timedelta(days=182)  # ~6 meses extra
    balance.extended = True
    balance.save(update_fields=['expires_at', 'extended'])

    CreditTransaction.objects.create(
        user=user,
        tipo='EXTENSION',
        monto_usd=Decimal('0.00'),
        descripcion='Extensión de expiración a 18 meses',
    )
    return balance

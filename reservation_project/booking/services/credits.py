# booking/services/credits.py
"""
Servicio para gestionar compra y uso de créditos TerraTokenX.
Implementación Premium con soporte para Locked Bonus y Ledger Audit.
"""
from datetime import timedelta
from decimal import Decimal
from django.db import transaction
from django.db.models import Sum, Q  # Added Q explicit import
from django.utils import timezone

from booking.models import CreditTransaction, UserProfile, TierConfig


LOCKED_BONUS_TIPO = "BONO"          # Tu tipo para cashback/bonos
USO_TIPO = "USO"
COMPRA_TIPO = "COMPRA"
EXPIRACION_TIPO = "EXPIRACION"

# “Marcador” en descripción para identificar bonus locked (simple y robusto sin migraciones)
LOCKED_TAG = "[LOCKED_INVEST_ONLY]"


def get_or_create_profile(user) -> UserProfile:
    """Obtiene o crea el perfil del usuario."""
    profile, _ = UserProfile.objects.get_or_create(user=user)
    return profile


def _today():
    return timezone.now().date()


def _is_expired_q():
    """
    Créditos vencidos: fecha_expiracion < hoy.
    Si fecha_expiracion es NULL => no vencen (o no aplica).
    """
    today = _today()
    return Q(fecha_expiracion__isnull=False) & Q(fecha_expiracion__lt=today)


def _sum_monto(qs) -> Decimal:
    val = qs.aggregate(total=Sum("monto"))["total"]
    return Decimal(val or 0)


def get_creditos_breakdown(user):
    """
    Devuelve breakdown “Premium”:
      - usable: créditos normales disponibles (no vencidos)
      - locked: créditos BONO locked disponibles (no vencidos)
      - total: usable + locked
    Nota: Se calcula desde ledger para que sea auditable y sin inconsistencias.
    """
    # Base: solo transacciones no vencidas
    base = CreditTransaction.objects.filter(user=user).exclude(_is_expired_q())

    # Locked BONO: filtramos por el marcador en descripción (incluye abonos tipo BONO y débitos tipo USO)
    locked_qs = base.filter(descripcion__contains=LOCKED_TAG)
    locked = _sum_monto(locked_qs)

    # Total disponible ledger = suma de todos los montos no vencidos
    total = _sum_monto(base)

    # Usable = total - locked
    usable = total - locked

    # Nunca devolvemos negativos por saneamiento (por si hay ajustes legacy)
    if locked < 0:
        locked = Decimal("0")
    if usable < 0:
        usable = Decimal("0")
    if total < 0:
        total = Decimal("0")

    return {
        "usable": usable.quantize(Decimal("0.01")),
        "locked": locked.quantize(Decimal("0.01")),
        "total": total.quantize(Decimal("0.01")),
    }


def get_creditos_disponibles(user):
    """
    Mantiene compatibilidad con tu uso actual: devuelve SOLO el total disponible.
    (Si quieres mostrar desglose en UI, usa get_creditos_breakdown).
    """
    # Usamos el breakdown para garantizar consistencia con el ledger
    return float(get_creditos_breakdown(user)["total"])


def usar_creditos(user, monto, descripcion, *, purpose="INVESTMENT"):
    """
    Descuenta créditos del usuario.

    - purpose:
        * "INVESTMENT"  -> permite usar bonos locked si hace falta
        * "OTHER"       -> NO permite usar bonos locked (fees, devoluciones, etc.)
    """
    monto = Decimal(str(monto))
    if monto <= 0:
        raise ValueError("El monto a descontar debe ser positivo.")

    profile = get_or_create_profile(user)

    with transaction.atomic():
        # Lock del perfil para evitar doble gasto en concurrencia
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        breakdown = get_creditos_breakdown(user)
        usable = breakdown["usable"]
        locked = breakdown["locked"]
        total = breakdown["total"]

        if total < monto:
            raise ValueError(f"Saldo insuficiente. Tienes ${total}, necesitas ${monto}")

        # Reglas Premium:
        # - Primero se consume USABLE
        # - Luego (solo si purpose=INVESTMENT) se puede consumir LOCKED
        usar_de_usable = min(usable, monto)
        restante = monto - usar_de_usable

        usar_de_locked = Decimal("0.00")
        if restante > 0:
            if purpose != "INVESTMENT":
                # No puede tocar locked (protección de reputación + trazabilidad)
                raise ValueError(
                    f"Créditos insuficientes en saldo usable (${usable}). "
                    f"Tienes ${locked} en BONO locked que solo puede usarse en nuevas inversiones."
                )
            # purpose=INVESTMENT => sí puede usar locked
            usar_de_locked = min(locked, restante)
            restante -= usar_de_locked

        if restante > 0:
            # Esto no debería ocurrir si total >= monto, pero lo dejamos por seguridad
            raise ValueError("No se pudo completar el débito de créditos por falta de saldo disponible.")

        # Registrar débitos separados para auditoría (Premium):
        # 1) Débito usable (si aplica)
        if usar_de_usable > 0:
            CreditTransaction.objects.create(
                user=user,
                monto=-usar_de_usable,
                tipo=USO_TIPO,
                metodo_pago="MANUAL",
                descripcion=f"{descripcion} [DEBIT_USABLE]"
            )

        # 2) Débito locked (si aplica) — queda explícito que fue inversión
        if usar_de_locked > 0:
            CreditTransaction.objects.create(
                user=user,
                monto=-usar_de_locked,
                tipo=USO_TIPO,
                metodo_pago="MANUAL",
                descripcion=f"{descripcion} {LOCKED_TAG} [DEBIT_LOCKED]"
            )

        # Actualizar saldo_creditos agregado (para compatibilidad UI/admin)
        # Sincronizamos con el ledger recalculado para evitar deriva
        new_breakdown = get_creditos_breakdown(user)
        profile.saldo_creditos = new_breakdown["total"]
        profile.save(update_fields=["saldo_creditos"])

    return True


def crear_bono_locked_invest(user, monto, descripcion, *, fecha_expiracion=None):
    """
    Crea un BONO locked “solo inversión”.
    Útil para tu cashback TTX/USDC por tier (incl. Diamond con TTX).
    """
    monto = Decimal(str(monto))
    if monto <= 0:
        raise ValueError("El monto del bono debe ser positivo.")

    profile = get_or_create_profile(user)

    with transaction.atomic():
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        CreditTransaction.objects.create(
            user=user,
            monto=monto,
            tipo=LOCKED_BONUS_TIPO,
            metodo_pago="MANUAL",
            descripcion=f"{descripcion} {LOCKED_TAG}",
            fecha_expiracion=fecha_expiracion
        )

        # Sync balance agregado
        breakdown = get_creditos_breakdown(user)
        profile.saldo_creditos = breakdown["total"]
        profile.save(update_fields=["saldo_creditos"])

    return True


def comprar_creditos(user, tier_nombre, cantidad_bloques=1, metodo_pago='MP', referencia=None):
    """
    Acredita créditos al usuario después de confirmar pago (Compra Standard).
    Ahora utiliza select_for_update y sincronización Ledger-Based.
    """
    tier_config = TierConfig.objects.get(nombre=tier_nombre)
    profile = get_or_create_profile(user)
    
    creditos_a_recibir = Decimal(1000 * cantidad_bloques)
    precio_total = tier_config.precio_por_1000_creditos * cantidad_bloques
    
    with transaction.atomic():
        # Lock para evitar concurrencia
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)
        
        # Verificar cap (Usamos el saldo actual en DB lockeada)
        if profile.saldo_creditos + creditos_a_recibir > tier_config.cap_creditos:
            raise ValueError(f"Excede el límite de {tier_config.cap_creditos} créditos para Tier {tier_nombre}")
        
        # Crear transacción de compra
        CreditTransaction.objects.create(
            user=user,
            monto=creditos_a_recibir,
            tipo=COMPRA_TIPO,
            metodo_pago=metodo_pago,
            descripcion=f'Compra de {creditos_a_recibir} créditos (Tier {tier_config.get_nombre_display()})',
            referencia_pago=referencia,
            # Expiración dinámica según el tier
            fecha_expiracion=timezone.now().date() + timedelta(days=tier_config.meses_validez_creditos * 30)
        )
        
        # Sincronizar saldo desde ledger (Más seguro que +=)
        breakdown = get_creditos_breakdown(user)
        profile.saldo_creditos = breakdown["total"]
        
        # Upgrade tier si aplica
        tier_order = ['BRONZE', 'SILVER', 'GOLD', 'BLACK']
        # Nota: aquí comparamos indices. Asegurarse que profile.tier sea válido.
        try:
            current_idx = tier_order.index(profile.tier)
            new_idx = tier_order.index(tier_nombre)
            if new_idx > current_idx:
                profile.tier = tier_nombre
        except ValueError:
            # Si el tier actual no está en la lista (legacy), forzamos upgrade si corresponde
            pass
        
        # Guardamos todo (saldo y tier)
        profile.save()
    
    return {'creditos': float(creditos_a_recibir), 'precio': precio_total}


def asignar_creditos_manual(user, monto, descripcion, admin_user=None):
    """
    Asigna créditos manualmente (para Gold/Black via concierge).
    """
    profile = get_or_create_profile(user)
    monto = Decimal(monto)
    
    with transaction.atomic():
        profile = UserProfile.objects.select_for_update().get(pk=profile.pk)

        CreditTransaction.objects.create(
            user=user,
            monto=monto,
            tipo='BONO', # Bono standard (usable)
            metodo_pago='MANUAL',
            descripcion=f'{descripcion} (Asignado por: {admin_user.username if admin_user else "Admin"})',
            # Expiración basada en el tier actual del usuario
            fecha_expiracion=timezone.now().date() + timedelta(days=get_expiration_days_for_user(user))
        )
        
        # Sync
        breakdown = get_creditos_breakdown(user)
        profile.saldo_creditos = breakdown["total"]
        profile.save(update_fields=["saldo_creditos"])
    
    return True


def get_tier_info(user):
    """Retorna información del tier actual del usuario."""
    profile = get_or_create_profile(user)
    # Usamos breakdown para mostrar info real del ledger si se quisiera
    # Por ahora mantenemos contrato de retorno simple
    saldo_real = get_creditos_disponibles(user) 
    
    try:
        tier_config = TierConfig.objects.get(nombre=profile.tier)
        return {
            'tier': profile.tier,
            'nombre_display': tier_config.get_nombre_display(),
            'saldo': saldo_real,
            'cap': tier_config.cap_creditos,
            'kyc_level': profile.kyc_level,
            'kyc_status': profile.kyc_status,
        }
    except TierConfig.DoesNotExist:
        return {
            'tier': profile.tier,
            'nombre_display': profile.tier,
            'saldo': saldo_real,
            'cap': 1000,
            'kyc_level': profile.kyc_level,
            'kyc_status': profile.kyc_status,
        }

def get_expiration_days_for_user(user):
    """
    Calcula los días de validez de créditos según el Tier del usuario.
    Standard/Gold -> 12 meses (~365 días)
    Platinum/Diamond -> 18 meses (~540 días)
    """
    try:
        profile = get_or_create_profile(user)
        tier_config = TierConfig.objects.get(nombre=profile.tier)
        return tier_config.meses_validez_creditos * 30
    except TierConfig.DoesNotExist:
        return 365  # Default 12 meses si falla config

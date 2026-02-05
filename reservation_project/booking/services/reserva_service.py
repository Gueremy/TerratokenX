# booking/services/reserva_service.py
"""
Servicio Premium para confirmación de pagos + Cashback.
Centraliza toda la lógica de confirmación para evitar duplicados.
Versión: v1.0 Premium (Aurora Certified)
"""
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from booking.models import Reserva, CreditTransaction, UserProfile


# ========================================
# CONFIGURACIÓN DE CASHBACK POR TIER
# ========================================
TIER_CASHBACK = {
    "BRONZE": Decimal("0.02"),  # 2%
    "SILVER": Decimal("0.05"),  # 5%
    "GOLD":   Decimal("0.08"),  # 8%
    "BLACK":  Decimal("0.10"),  # 10%
}

DIAMOND_TTX_CASHBACK = Decimal("0.15")  # 15% si paga con TTX (KYC Diamond)


# ========================================
# FUNCIÓN: EMITIR CASHBACK (IDEMPOTENTE)
# ========================================
def emitir_cashback_reserva(reserva):
    """
    Emite un bono cashback LOCKED para inversión, basado en Tier y regla Diamond+TTX.
    
    - Source of Truth: reserva.total (USD).
    - Registra CreditTransaction con tag [CASHBACK_RESERVA].
    - Idempotente: No emite si ya existe un cashback para esta reserva.
    
    Returns:
        True si se emitió, None si ya existía o no aplica.
    """
    from booking.services.credits import crear_bono_locked_invest, get_or_create_profile
    
    user = reserva.usuario
    if not user:
        return None
    
    profile = get_or_create_profile(user)
    monto_usd = Decimal(str(reserva.total)).quantize(Decimal("0.01"))
    
    # Determinar porcentaje según Tier
    porcentaje = TIER_CASHBACK.get(profile.tier, Decimal("0.02"))
    
    # Regla especial Diamond: 15% si paga con TTX
    crypto_currency = (getattr(reserva, "crypto_currency", "") or "").upper()
    is_diamond = getattr(profile, "kyc_level", 0) >= 3
    paid_with_ttx = crypto_currency == "TTX"
    
    if is_diamond and paid_with_ttx:
        porcentaje = DIAMOND_TTX_CASHBACK
    
    # Calcular monto del bono
    monto_bono = (monto_usd * porcentaje).quantize(Decimal("0.01"))
    if monto_bono <= 0:
        return None
    
    # Descripción con tags para trazabilidad
    descripcion = (
        f"[CASHBACK_RESERVA] Cashback {int(porcentaje * 100)}% por Inversión "
        f"#{reserva.numero_reserva} (Tier {profile.tier})"
    )
    
    # IDEMPOTENCIA: Verificar si ya existe cashback para esta reserva
    # Nota: Django no permite múltiples icontains en el mismo campo, usamos Q objects
    from django.db.models import Q
    ya_existe = CreditTransaction.objects.filter(
        Q(user=user) &
        Q(tipo="BONO") &
        Q(descripcion__icontains="[CASHBACK_RESERVA]") &
        Q(descripcion__icontains=str(reserva.numero_reserva))
    ).exists()
    
    if ya_existe:
        return None  # Ya se emitió antes
    
    # Emitir bono locked
    return crear_bono_locked_invest(user, monto_bono, descripcion)


# ========================================
# FUNCIÓN CENTRAL: CONFIRMAR RESERVA PAGO
# ========================================
def confirm_reserva_pago(reserva, *, metodo_pago=None, referencia_pago=None):
    """
    Confirmación ÚNICA e IDEMPOTENTE para pagos.
    
    Ejecuta todas las acciones premium una sola vez:
    1. Cambio de estado a CONFIRMADO
    2. Emisión de cashback (si aplica)
    3. Disparo de FirmaVirtual y emails (en Reserva.save)
    
    Args:
        reserva: Instancia de Reserva o ID
        metodo_pago: Opcional, para actualizar el método (MP, CRYPTO, CREDITS)
        referencia_pago: Opcional, ID de transacción externa
    
    Returns:
        True si se confirmó, False si ya estaba confirmado.
    """
    # Permitir pasar ID o instancia
    if isinstance(reserva, int):
        reserva = Reserva.objects.get(pk=reserva)
    
    with transaction.atomic():
        # Lock para evitar race conditions
        r = Reserva.objects.select_for_update().get(pk=reserva.pk)
        
        # Idempotencia: Si ya está confirmado, no hacer nada
        if r.estado_pago == Reserva.ESTADO_CONFIRMADO:
            return False
        
        # Actualizar estado
        r.estado_pago = Reserva.ESTADO_CONFIRMADO
        
        if metodo_pago:
            r.metodo_pago = metodo_pago
        
        # Guardar (esto dispara emails y FirmaVirtual automáticamente)
        r.save()
    
    # Efectos externos (fuera de la transacción)
    # El cashback se ejecuta de forma separada pero idempotente
    try:
        emitir_cashback_reserva(r)
    except Exception as e:
        # Log pero no fallar la confirmación
        import logging
        logging.getLogger(__name__).error(f"Error emitiendo cashback: {e}")
    
    return True


# ========================================
# FUNCIÓN: APROBAR RESERVA (PARA ADMIN)
# ========================================
def admin_aprobar_reserva(reserva_id, admin_user=None):
    """
    Shortcut para que el admin apruebe una reserva desde el panel.
    Útil para pagos CRYPTO_MANUAL en revisión.
    
    Args:
        reserva_id: ID de la reserva a aprobar
        admin_user: Usuario admin que aprueba (para log)
    
    Returns:
        (success: bool, message: str)
    """
    try:
        reserva = Reserva.objects.get(pk=reserva_id)
    except Reserva.DoesNotExist:
        return (False, "Reserva no encontrada")
    
    if reserva.estado_pago == Reserva.ESTADO_CONFIRMADO:
        return (False, "La reserva ya está confirmada")
    
    # Confirmar usando la función central
    resultado = confirm_reserva_pago(reserva)
    
    if resultado:
        # Log de auditoría
        import logging
        logger = logging.getLogger(__name__)
        admin_name = admin_user.username if admin_user else "Sistema"
        logger.info(f"[ADMIN] Reserva #{reserva.numero_reserva} aprobada por {admin_name}")
        
        return (True, f"Reserva #{reserva.numero_reserva} confirmada exitosamente")
    else:
        return (False, "No se pudo confirmar la reserva")

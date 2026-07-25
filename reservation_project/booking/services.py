"""Capa de services: TODA la lógica de negocio vive aquí.

Las views solo reciben input, llaman un service y devuelven output.
Los services no conocen HTTP.
"""

import logging
from datetime import timedelta
from decimal import Decimal

from django.conf import settings
from django.db import transaction
from django.utils import timezone

from .constants import EstadoPago, KYC_LIMITS_USD
from .exceptions import (
    DropInactivo,
    IdempotenciaError,
    LimiteKYCSuperado,
    StockInsuficiente,
)
from .models import AuditLog, ProjectDrop, Reserva, UserProfile
from .selectors import get_drop_activo

logger = logging.getLogger('booking')

# Ventana en la que dos checkouts idénticos se consideran el mismo (doble click)
VENTANA_IDEMPOTENCIA_SEGUNDOS = 60


def _buscar_reserva_duplicada(user, proyecto_id: int, cantidad_tokens: int, metodo_pago: str):
    """
    Detecta un reenvío del mismo checkout (doble click, retry del cliente).

    Devuelve la reserva PENDIENTE idéntica creada dentro de la ventana de
    idempotencia, o None. Evita duplicar reservas y descontar stock dos veces.
    """
    ventana = timezone.now() - timedelta(seconds=VENTANA_IDEMPOTENCIA_SEGUNDOS)
    return Reserva.objects.filter(
        user=user,
        proyecto_id=proyecto_id,
        cantidad_tokens=cantidad_tokens,
        metodo_pago=metodo_pago,
        estado_pago=EstadoPago.PENDIENTE,
        created_at__gte=ventana,
    ).order_by('-created_at').first()


def validar_compra(proyecto_id: int, user, cantidad_tokens: int, metodo_pago: str):
    """
    Valida que la compra sea posible.
    Devuelve (drop_activo, precio_total) o lanza excepción.
    No modifica nada en DB — solo valida.
    """
    # 1. Verificar Drop activo
    drop = get_drop_activo(proyecto_id)
    if not drop:
        raise DropInactivo("No hay una ventana de venta activa para este proyecto")

    # 2. Verificar stock
    if drop.stock_disponible < cantidad_tokens:
        raise StockInsuficiente(f"Solo quedan {drop.stock_disponible} tokens disponibles")

    # 3. Verificar límite KYC
    precio_unitario = drop.precio_override or drop.proyecto.precio_token
    total_esta_compra = Decimal(precio_unitario) * cantidad_tokens

    perfil = UserProfile.objects.get_or_create(user=user)[0]
    limite_usd = Decimal(str(KYC_LIMITS_USD.get(perfil.kyc_tier, 1000)))
    if perfil.investment_total_usd + total_esta_compra > limite_usd:
        raise LimiteKYCSuperado(
            f"Esta compra supera tu límite para tier {perfil.kyc_tier}. "
            f"Límite: ${limite_usd} USD. Acumulado: ${perfil.investment_total_usd}"
        )

    return drop, total_esta_compra


@transaction.atomic
def crear_reserva_pendiente(
    proyecto_id: int,
    user,
    cantidad_tokens: int,
    metodo_pago: str,
    creditos_aplicar: Decimal = Decimal('0.00'),
) -> Reserva:
    """
    Crea la Reserva en estado PENDIENTE y descuenta el stock del Drop.
    El pago se confirma después vía webhook.
    """
    drop, total = validar_compra(proyecto_id, user, cantidad_tokens, metodo_pago)

    # Idempotencia: un doble click no debe crear dos reservas ni descontar
    # el stock dos veces. Se reutiliza la reserva PENDIENTE idéntica reciente.
    duplicada = _buscar_reserva_duplicada(user, proyecto_id, cantidad_tokens, metodo_pago)
    if duplicada is not None:
        logger.info(
            "Compra duplicada detectada para %s: se reutiliza la reserva %s",
            user.username, duplicada.numero_reserva,
        )
        return duplicada

    # Bloquear el Drop para evitar race condition
    drop = ProjectDrop.objects.select_for_update().get(id=drop.id)

    # Re-verificar stock después del lock (puede haber cambiado)
    if drop.stock_disponible < cantidad_tokens:
        raise StockInsuficiente(f"Solo quedan {drop.stock_disponible} tokens disponibles")

    # Descontar stock
    drop.stock_disponible -= cantidad_tokens
    drop.save(update_fields=['stock_disponible'])

    # Aplicar créditos (los fees se calculan ANTES, ver services_creditos).
    # Nunca se descuenta más de lo que cuesta la compra: aplicar $500 a una
    # compra de $100 debe consumir $100 de créditos, no quemar los $400 restantes.
    total_final = total
    if creditos_aplicar and creditos_aplicar > 0:
        from .services_creditos import aplicar_credito_en_checkout
        a_aplicar = min(creditos_aplicar, total)
        descontado = aplicar_credito_en_checkout(user, a_aplicar, reserva=None)
        total_final = max(total - descontado, Decimal('0.00'))

    # Crear reserva (total manual: el precio del Drop manda, no el precio base)
    reserva = Reserva(
        user=user,
        nombre=(user.get_full_name() or user.username),
        correo=user.email,
        proyecto_id=proyecto_id,
        cantidad_tokens=cantidad_tokens,
        total=total_final,
        estado_pago=EstadoPago.PENDIENTE,
        metodo_pago=metodo_pago,
    )
    reserva._total_manual = True
    reserva.save()

    logger.info(
        "Reserva %s creada: %s tokens del proyecto %s (total $%s)",
        reserva.numero_reserva, cantidad_tokens, proyecto_id, total_final,
    )
    return reserva


@transaction.atomic
def confirmar_reserva(reserva_id: int) -> Reserva:
    """
    Confirma el pago de una reserva.
    Se llama desde los webhooks de MP, Cryptomus y Kushki.
    Idempotente: segunda llamada lanza IdempotenciaError.

    Los contadores (tokens_vendidos, investment_total_usd) y el email de
    bienvenida se disparan en Reserva.save() al detectar la transición.
    """
    reserva = Reserva.objects.select_for_update().select_related(
        'user', 'proyecto'
    ).get(id=reserva_id)

    if reserva.estado_pago == EstadoPago.CONFIRMADO:
        raise IdempotenciaError(f"Reserva {reserva_id} ya confirmada")

    reserva.estado_pago = EstadoPago.CONFIRMADO
    reserva._total_manual = True  # preservar el total pactado (precio de Drop / créditos)
    reserva.save()

    AuditLog.registrar(
        accion='reserva.confirmada',
        objeto=reserva,
        user=reserva.user,
        datos_despues={'estado': 'CONFIRMADO', 'total': str(reserva.total)},
    )
    return reserva


def expirar_reservas_pendientes(minutos: int = None) -> int:
    """
    Libera el stock de reservas PENDIENTE abandonadas.

    Sin esto, un carrito abandonado retiene tokens para siempre y el Drop
    aparece agotado sin haber vendido. La ventana debe superar el lifetime
    del invoice de Cryptomus (1 h) para no cancelar pagos en curso.

    Devuelve cuántas reservas se liberaron.
    """
    if minutos is None:
        minutos = getattr(settings, 'RESERVA_PENDIENTE_TIMEOUT_MINUTOS', 90)

    limite = timezone.now() - timedelta(minutes=minutos)
    vencidas = Reserva.objects.filter(
        estado_pago=EstadoPago.PENDIENTE,
        created_at__lt=limite,
    ).values_list('id', flat=True)

    liberadas = 0
    for reserva_id in list(vencidas):
        try:
            marcar_reserva_fallida(
                reserva_id,
                EstadoPago.RECHAZADO,
                motivo=f'expirada: sin pago tras {minutos} minutos',
            )
            liberadas += 1
        except IdempotenciaError:
            continue  # se confirmó entre el listado y el procesamiento
        except Exception as e:
            logger.error("Error expirando la reserva %s: %s", reserva_id, e)

    if liberadas:
        logger.info("Reservas expiradas y stock liberado: %s", liberadas)
    return liberadas


@transaction.atomic
def marcar_reserva_fallida(reserva_id: int, nuevo_estado: str, motivo: str = '') -> Reserva:
    """
    Marca una reserva como FALLIDA/RECHAZADA y devuelve el stock al Drop activo.
    Usado por los webhooks cuando el pago falla o se cancela.
    """
    reserva = Reserva.objects.select_for_update().get(id=reserva_id)

    if reserva.estado_pago == EstadoPago.CONFIRMADO:
        raise IdempotenciaError(f"Reserva {reserva_id} ya confirmada — no se puede marcar fallida")
    if reserva.estado_pago in (EstadoPago.FALLIDO, EstadoPago.RECHAZADO):
        return reserva  # ya procesada

    reserva.estado_pago = nuevo_estado
    reserva.save(update_fields=['estado_pago', 'updated_at'])

    # Devolver stock al drop activo del proyecto (si existe)
    drop = get_drop_activo(reserva.proyecto_id) if reserva.proyecto_id else None
    if drop is None and reserva.proyecto_id:
        # Si el drop se agotó justo con esta reserva, buscar el último drop del proyecto
        drop = ProjectDrop.objects.filter(proyecto_id=reserva.proyecto_id).order_by('-numero').first()
    if drop:
        drop = ProjectDrop.objects.select_for_update().get(id=drop.id)
        drop.stock_disponible = min(drop.stock_disponible + reserva.cantidad_tokens, drop.stock_total)
        drop.save(update_fields=['stock_disponible'])

    AuditLog.registrar(
        accion='reserva.fallida',
        objeto=reserva,
        datos_despues={'estado': nuevo_estado, 'motivo': motivo},
    )
    return reserva

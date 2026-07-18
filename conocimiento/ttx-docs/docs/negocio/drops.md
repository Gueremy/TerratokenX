# Sistema de Drops — TerraTokenX

## Concepto

Un Drop es una ventana de venta con stock limitado y tiempo definido.
Sin Drop activo → no se puede comprar. El FOMO es intencional.

Estructura 30/30/40:
- **Drop 1:** 30% del total de tokens. Mayor descuento. Ventana corta.
- **Drop 2:** 30% del total. Precio ajustado por demanda.
- **Drop 3:** 40% del total. Cierre. Precio más alto.

---

## Estados del Drop

```
PENDIENTE → ACTIVO → CERRADO
              ↓
           AGOTADO (stock llega a 0 antes de que venza la fecha)
```

Transiciones válidas:
- Solo Joan puede activar un Drop manualmente (o automáticamente por fecha).
- Solo Joan puede cerrar un Drop anticipadamente.
- Un proyecto puede tener a lo sumo 1 Drop ACTIVO a la vez.

---

## exceptions.py

```python
# booking/exceptions.py

class DropInactivo(Exception):
    """No hay Drop activo para este proyecto."""
    pass

class StockInsuficiente(Exception):
    """El Drop no tiene suficiente stock para la cantidad solicitada."""
    pass

class LimiteKYCSuperado(Exception):
    """El usuario superaría su límite KYC con esta compra."""
    pass

class CreditoInsuficiente(Exception):
    """Saldo de créditos insuficiente para la operación."""
    pass

class DropYaCerrado(Exception):
    """El Drop ya fue cerrado o está fuera de su ventana de tiempo."""
    pass

class IdempotenciaError(Exception):
    """La operación ya fue procesada anteriormente."""
    pass
```

---

## selectors.py — Queries de Drops

```python
# booking/selectors.py
from django.utils import timezone
from .models import ProjectDrop, Proyecto


def get_drop_activo(proyecto_id: int) -> ProjectDrop | None:
    """
    Devuelve el Drop activo del proyecto, o None si no hay ninguno.
    Un Drop es activo si:
      - activo=True
      - fecha_inicio <= now() <= fecha_fin
      - stock_disponible > 0
    """
    ahora = timezone.now()
    return ProjectDrop.objects.filter(
        proyecto_id=proyecto_id,
        activo=True,
        fecha_inicio__lte=ahora,
        fecha_fin__gte=ahora,
        stock_disponible__gt=0,
    ).select_related('proyecto').first()


def get_stock_disponible(drop_id: int) -> int:
    """Devuelve el stock disponible del Drop. Lanza DoesNotExist si no existe."""
    return ProjectDrop.objects.values_list(
        'stock_disponible', flat=True
    ).get(id=drop_id)


def list_drops_proyecto(proyecto_id: int):
    """Todos los drops de un proyecto, ordenados por número."""
    return ProjectDrop.objects.filter(
        proyecto_id=proyecto_id
    ).order_by('numero')
```

---

## services.py — Lógica de Drops

```python
# booking/services.py
from decimal import Decimal
from django.db import transaction
from django.utils import timezone

from .models import ProjectDrop, Reserva, Proyecto
from .exceptions import (
    DropInactivo, StockInsuficiente, LimiteKYCSuperado, IdempotenciaError
)
from .selectors import get_drop_activo
from .constants import EstadoPago, MetodoPago, KYC_LIMITS_USD


def validar_compra(
    proyecto_id: int,
    user,
    cantidad_tokens: int,
    metodo_pago: str,
) -> tuple[ProjectDrop, Decimal]:
    """
    Valida que la compra sea posible.
    Devuelve (drop_activo, precio_total) o lanza excepción.
    No modifica nada en DB — solo valida.
    """
    # 1. Verificar Drop activo
    drop = get_drop_activo(proyecto_id)
    if not drop:
        raise DropInactivo(
            "No hay una ventana de venta activa para este proyecto"
        )

    # 2. Verificar stock
    if drop.stock_disponible < cantidad_tokens:
        raise StockInsuficiente(
            f"Solo quedan {drop.stock_disponible} tokens disponibles"
        )

    # 3. Verificar límite KYC
    precio_unitario = drop.precio_override or drop.proyecto.precio_token
    total_esta_compra = precio_unitario * cantidad_tokens

    perfil = user.userprofile
    limite_usd = KYC_LIMITS_USD.get(perfil.kyc_tier, 1000)
    if perfil.investment_total_usd + total_esta_compra > Decimal(str(limite_usd)):
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
    El pago se confirma después via webhook.
    """
    drop, total = validar_compra(proyecto_id, user, cantidad_tokens, metodo_pago)

    # Bloquear el Drop para evitar race condition
    drop = ProjectDrop.objects.select_for_update().get(id=drop.id)

    # Re-verificar stock después del lock (puede haber cambiado)
    if drop.stock_disponible < cantidad_tokens:
        raise StockInsuficiente(
            f"Solo quedan {drop.stock_disponible} tokens disponibles"
        )

    # Descontar stock
    drop.stock_disponible -= cantidad_tokens
    drop.save(update_fields=['stock_disponible'])

    # Calcular total con créditos
    from .services_creditos import validar_y_reservar_creditos
    total_final = total - creditos_aplicar
    if total_final < 0:
        total_final = Decimal('0.00')

    # Crear reserva
    reserva = Reserva.objects.create(
        user=user,
        proyecto_id=proyecto_id,
        cantidad_tokens=cantidad_tokens,
        total=total_final,
        estado_pago=EstadoPago.PENDIENTE,
        metodo_pago=metodo_pago,
    )

    return reserva


@transaction.atomic
def confirmar_reserva(reserva_id: int) -> Reserva:
    """
    Confirma el pago de una reserva.
    Se llama desde los webhooks de MP, Cryptomus, Kushki.
    """
    reserva = Reserva.objects.select_for_update().select_related(
        'user__userprofile', 'proyecto'
    ).get(id=reserva_id)

    # Idempotencia
    if reserva.estado_pago == EstadoPago.CONFIRMADO:
        raise IdempotenciaError(f"Reserva {reserva_id} ya confirmada")

    reserva.estado_pago = EstadoPago.CONFIRMADO
    reserva.save(update_fields=['estado_pago'])

    # Actualizar tokens vendidos del proyecto
    Proyecto.objects.filter(id=reserva.proyecto_id).update(
        tokens_vendidos=models.F('tokens_vendidos') + reserva.cantidad_tokens
    )

    # Actualizar inversión acumulada del usuario
    UserProfile.objects.filter(user=reserva.user).update(
        investment_total_usd=models.F('investment_total_usd') + reserva.total
    )

    # AuditLog
    from .models import AuditLog
    AuditLog.registrar(
        accion='reserva.confirmada',
        objeto=reserva,
        datos_despues={'estado': 'CONFIRMADO', 'total': str(reserva.total)},
    )

    # Email async (fuera del ciclo de confirmación, no bloquea)
    from .tasks import enviar_email_confirmacion_task
    enviar_email_confirmacion_task.delay(reserva_id)

    # Blockchain mint (Fase 3 — solo si tiene wallet)
    if hasattr(reserva.user, 'userprofile') and reserva.user.userprofile.wallet_address:
        from .tasks import mint_token_task
        mint_token_task.delay(reserva_id)

    return reserva
```

---

## Verificación de tarea completada

```bash
# La tarea de Drops está completa cuando:

# 1. get_drop_activo devuelve None si no hay drop activo
python manage.py shell -c "
from booking.selectors import get_drop_activo
result = get_drop_activo(99999)  # ID que no existe
assert result is None, 'Debe devolver None para proyecto sin drop'
print('✅ get_drop_activo OK')
"

# 2. Race condition cubierta (test en docs/infra/testing.md §race-conditions)
pytest booking/tests/test_drops.py::test_race_condition_stock -v

# 3. manage.py check 0 errores
python manage.py check
```

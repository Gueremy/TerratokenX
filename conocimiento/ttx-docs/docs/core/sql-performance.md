# SQL Performance — TerraTokenX

## La regla de oro

**Si una query puede afectar dinero real, usa `select_for_update()` + `@transaction.atomic`.**
**Si una query se ejecuta más de 10 veces por minuto, revisa si necesita índice.**

---

## select_related vs prefetch_related

```python
# select_related → FK y OneToOne (hace JOIN en SQL, 1 query)
Reserva.objects.select_related('user', 'proyecto', 'user__userprofile')

# prefetch_related → FK inversa y ManyToMany (2 queries separadas + join en Python)
Proyecto.objects.prefetch_related('drops', 'imagenes', 'documentos')

# Combinado — patrón para el marketplace
Proyecto.objects.select_related('owner__userprofile') \
                .prefetch_related('drops', 'imagenes') \
                .filter(activo=True)
```

---

## select_for_update — OBLIGATORIO en operaciones financieras

```python
# ✅ Correcto — bloquea la fila durante la transacción
@transaction.atomic
def descontar_stock(drop_id: int, cantidad: int) -> None:
    drop = ProjectDrop.objects.select_for_update().get(id=drop_id)
    if drop.stock_disponible < cantidad:
        raise StockInsuficiente(
            f"Stock disponible: {drop.stock_disponible}, requerido: {cantidad}"
        )
    drop.stock_disponible -= cantidad
    drop.save(update_fields=['stock_disponible'])


@transaction.atomic
def aplicar_credito(user_id: int, monto: Decimal) -> None:
    balance = CreditBalance.objects.select_for_update().get(user_id=user_id)
    if balance.balance_usd < monto:
        raise CreditoInsuficiente(
            f"Saldo: {balance.balance_usd}, requerido: {monto}"
        )
    balance.balance_usd -= monto
    balance.save(update_fields=['balance_usd'])
```

Sin `select_for_update`, dos requests simultáneos pueden leer el mismo stock
y ambos pasar la validación → sobreventa.

---

## @transaction.atomic — cuándo usar

Usar siempre que una operación modifique más de una tabla:

```python
# Confirmación de reserva: toca Reserva + CreditTransaction + AuditLog
@transaction.atomic
def confirmar_reserva(reserva_id: int) -> Reserva:
    reserva = Reserva.objects.select_for_update().get(id=reserva_id)
    # ... lógica ...
    reserva.save()
    CreditTransaction.objects.create(...)   # dentro del atomic block
    AuditLog.registrar(...)                 # dentro del atomic block
    # Si cualquier línea falla → todo se revierte automáticamente

    # El email va FUERA del atomic block (no es crítico para consistencia)
    enviar_email_confirmacion.delay(reserva_id)   # Celery task
    return reserva
```

---

## only() y defer() — no traer lo que no se usa

```python
# Marketplace: no necesita gps_data (JSON pesado) ni legal_hash
Proyecto.objects.only(
    'id', 'nombre', 'slug', 'precio_token',
    'tokens_totales', 'tokens_vendidos', 'activo', 'owner_type'
)

# defer() — traer todo excepto campos pesados
Proyecto.objects.defer('gps_data', 'docs_manifest_hash')
```

---

## Aggregations en DB, no en Python

```python
# ❌ MALO — 100 proyectos = 100 queries
total = sum(r.total for r in Reserva.objects.filter(proyecto=p))

# ✅ BUENO — 1 query
from django.db.models import Sum, Count, Avg, F

total = Reserva.objects.filter(
    proyecto=proyecto,
    estado_pago=EstadoPago.CONFIRMADO
).aggregate(total=Sum('total'))['total'] or Decimal('0.00')

# Tokens vendidos — actualizar en DB, no calcular en Python
Proyecto.objects.filter(id=proyecto_id).update(
    tokens_vendidos=F('tokens_vendidos') + cantidad_tokens
)
```

---

## Índices requeridos

Están declarados en Meta.indexes de cada modelo. Los más críticos:

```python
# Reserva — búsquedas frecuentes
models.Index(fields=['user', 'estado_pago'])  # historial del inversor
models.Index(fields=['mp_payment_id'])         # webhook MP
models.Index(fields=['cryptomus_uuid'])        # webhook Cryptomus

# CreditBalance — cron de expiración
models.Index(fields=['expires_at', 'tier'])

# ProjectDrop — marketplace
models.Index(fields=['proyecto', 'activo'])

# AuditLog — panel Joan
models.Index(fields=['accion', 'created_at'])
```

---

## Connection Pooling

```python
# settings/production.py
DATABASES = {
    'default': {
        ...
        'CONN_MAX_AGE': 60,     # reutiliza conexiones 60 segundos
        'CONN_HEALTH_CHECKS': True,
    }
}
```

---

## Debugging de queries en desarrollo

```python
# settings/local.py — ver SQL en consola
LOGGING = {
    'version': 1,
    'loggers': {
        'django.db.backends': {
            'level': 'DEBUG',
            'handlers': ['console'],
        }
    }
}

# Ver la query de un queryset específico
print(Proyecto.objects.filter(activo=True).query)

# Contar queries en un bloque
from django.test.utils import override_settings
from django.db import connection, reset_queries
reset_queries()
# ... código ...
print(f"Queries ejecutadas: {len(connection.queries)}")
```

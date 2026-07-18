# Seguridad — TerraTokenX

## Vulnerabilidades críticas específicas de TerraTokenX

---

### 1. Race Condition — Stock de Drops (PRIORIDAD MÁXIMA)

**El escenario:** Usuario A y B hacen click en "Comprar" con 1 token disponible.
Ambos leen `stock_disponible = 1`. Ambos pasan la validación. Stock queda en -1.

**Solución obligatoria:**

```python
@transaction.atomic
def reservar_tokens(drop_id: int, user_id: int, cantidad: int) -> Reserva:
    # select_for_update() bloquea la fila hasta que termine la transacción
    drop = ProjectDrop.objects.select_for_update().get(id=drop_id)

    if not drop.activo:
        raise DropInactivo("No hay Drop activo para este proyecto")
    if drop.stock_disponible < cantidad:
        raise StockInsuficiente(
            f"Stock: {drop.stock_disponible}, solicitado: {cantidad}"
        )

    drop.stock_disponible -= cantidad
    drop.save(update_fields=['stock_disponible'])

    reserva = Reserva.objects.create(
        user_id=user_id, cantidad_tokens=cantidad, ...
    )
    return reserva
```

---

### 2. Race Condition — Double-Spend de Créditos

**El escenario:** Usuario abre dos pestañas, hace checkout simultáneo con $100 en créditos.
Ambas requests leen `balance_usd = 100`. Ambas aplican $100. Consigue $200 por $100.

**Solución:** `select_for_update()` en `CreditBalance` — ver `docs/core/sql-performance.md`.

---

### 3. Webhook Replay Attack

**El escenario:** Atacante renvía un webhook legítimo de Cryptomus 10 veces.
Sin protección → 10 confirmaciones del mismo pago.

**Solución — idempotencia con `cryptomus_uuid` único:**

```python
def procesar_webhook_cryptomus(data: dict) -> None:
    uuid = data.get('uuid')
    status = data.get('status')

    # Idempotencia: si ya procesamos este UUID, ignorar silenciosamente
    if Reserva.objects.filter(cryptomus_uuid=uuid,
                               estado_pago=EstadoPago.CONFIRMADO).exists():
        logger.info('webhook.duplicado', extra={'uuid': uuid})
        return   # 200 OK para que Cryptomus no reintente

    if status == 'paid':
        reserva = Reserva.objects.get(cryptomus_uuid=uuid)
        confirmar_reserva(reserva.id)
```

---

### 4. Webhook Falso — Sin Verificar Firma

**El escenario:** Atacante conoce la URL del webhook (es pública).
Envía POST con `{"status": "paid"}` inventado. Sin verificación → reserva confirmada sin pago.

**Solución MercadoPago:**

```python
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
    received = request.headers.get('x-signature', '').split(',')[0].split('=')[-1]
    return hmac.compare_digest(expected, received)
```

**Solución Cryptomus:**

```python
import hashlib, base64, json

def verificar_firma_cryptomus(request) -> bool:
    body = request.body
    body_b64 = base64.b64encode(body).decode()
    expected = hashlib.md5(
        f"{body_b64}{settings.CRYPTOMUS_PAYMENT_API_KEY}".encode()
    ).hexdigest()
    received = request.headers.get('sign', '')
    return hmac.compare_digest(expected, received)
```

**Solución Didit:**

```python
import hmac, hashlib

def verificar_firma_didit(request) -> bool:
    body = request.body
    expected = hmac.new(
        settings.DIDIT_WEBHOOK_SECRET.encode(),
        body,
        hashlib.sha256
    ).hexdigest()
    received = request.headers.get('x-didit-signature', '')
    return hmac.compare_digest(expected, received)
```

---

### 5. Broken Object Level Authorization

**El escenario:** `GET /api/reservas/77/` devuelve la reserva de cualquier usuario.
Un inversor itera IDs y ve reservas de otros.

**Solución en cada endpoint:**

```python
class ReservaDetailView(RetrieveAPIView):
    def get_object(self):
        return get_object_or_404(
            Reserva,
            id=self.kwargs['pk'],
            user=self.request.user   # ← SIEMPRE filtrar por usuario autenticado
        )
```

---

### 6. File Upload — KYC y Data Room

```python
ALLOWED_KYC_TYPES = ['image/jpeg', 'image/png', 'application/pdf']
MAX_FILE_SIZE_MB = 10

def validate_uploaded_file(file):
    if file.content_type not in ALLOWED_KYC_TYPES:
        raise ValidationError("Tipo de archivo no permitido")
    if file.size > MAX_FILE_SIZE_MB * 1024 * 1024:
        raise ValidationError(f"Archivo máximo {MAX_FILE_SIZE_MB}MB")

def get_safe_filename(file) -> str:
    """Nunca usar el nombre original del usuario — path traversal."""
    ext = os.path.splitext(file.name)[1].lower()
    return f"{uuid.uuid4()}{ext}"
```

---

### 7. Balance Negativo de Créditos

```python
# En el serializer del checkout:
creditos_aplicar = serializers.DecimalField(
    max_digits=10, decimal_places=2,
    min_value=Decimal('0.00'),
    required=False, default=Decimal('0.00')
)

# En el service:
def aplicar_credito(user_id: int, monto: Decimal) -> None:
    if monto <= 0:
        return  # nada que aplicar
    balance = CreditBalance.objects.select_for_update().get(user_id=user_id)
    if monto > balance.balance_usd:
        raise CreditoInsuficiente(
            f"Saldo disponible: ${balance.balance_usd}"
        )
```

---

### 8. Injection en GPS Data

```python
class GPSDataSerializer(serializers.Serializer):
    lat  = serializers.FloatField(min_value=-90,  max_value=90)
    lng  = serializers.FloatField(min_value=-180, max_value=180)
    zoom = serializers.IntegerField(min_value=1,  max_value=20, required=False)

# Validar ANTES de guardar en gps_data JSONField
```

---

## Checklist de seguridad pre-deploy

```
□ DEBUG=False
□ SECRET_KEY no es el valor por defecto de Django
□ ALLOWED_HOSTS sin comodín (*)
□ CORS_ALLOWED_ORIGINS con dominios reales (sin *)
□ Todos los webhooks verifican firma antes de procesar
□ Todos los endpoints financieros tienen select_for_update()
□ Todos los endpoints tienen object-level permission (filtrar por user)
□ File uploads validan tipo y tamaño
□ Sin referencias a FirmaVirtual (grep -r "firmavirtual" --include="*.py")
□ Sin API keys hardcodeadas (grep -r "APP_USR\|SG\.\|re_" --include="*.py")
□ bandit -r booking/ -ll  (0 hallazgos high/medium)
□ pip-audit  (0 vulnerabilidades críticas)
```

---

## Guardrails del agente (Claude Code)

Reglas específicas para cuando Claude Code hace cambios automáticos:

### Regla de un cambio a la vez

```
NUNCA encadenar:
  - Modificar models.py  →  hacer migración  →  actualizar services.py
  en una sola operación.

SIEMPRE:
  1. Modificar models.py
  2. manage.py check → ✅
  3. makemigrations y revisar la migración generada
  4. migrate
  5. Solo entonces tocar services.py
```

### Protocolo para migraciones destructivas

Antes de eliminar un campo que tiene datos:

```bash
# 1. Backup de la tabla afectada
python manage.py dumpdata booking.reserva > backup_reserva_$(date +%Y%m%d).json

# 2. Verificar cuántos registros tienen ese campo con datos
python manage.py shell -c "
from booking.models import Reserva
print(Reserva.objects.exclude(firmavirtual_id='').count())
"

# 3. Solo si el count es 0 o los datos son descartables, proceder
# 4. Hacer la migración
# 5. Verificar que manage.py check sigue en 0 errores
```

### Trigger de rollback automático

Si `manage.py check` devuelve errores después de un cambio:

```bash
git checkout -- booking/models.py   # revertir el archivo específico
# O si se hizo commit:
git revert HEAD --no-edit
```

### Lo que Claude Code NUNCA debe hacer sin confirmación

- Eliminar migraciones existentes
- Modificar datos en producción directamente
- Cambiar nombres de URL (el frontend depende de ellos)
- Ejecutar `migrate --fake`
- Borrar archivos de `booking/migrations/` que no sean `__pycache__`

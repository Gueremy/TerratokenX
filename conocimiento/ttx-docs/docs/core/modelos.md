# Modelos — TerraTokenX

## Estado actual

Los modelos que EXISTEN y funcionan (QA-02 PASS):
`Proyecto`, `Reserva`, `ProjectDrop`, `UserProfile`, `Coupon`,
`ProyectoImagen`, `ProyectoSeccion`, `ProyectoDocumento`,
`Configuracion`, `DiaFeriado`

Los modelos que HAY QUE CREAR en Semana 2:
`CreditBalance`, `CreditTransaction`, `TierConfig`, `FeeConfig`,
`AuditLog`, `FraccionadorProfile`, `RetiroFraccionador`

---

## Base: SoftDeleteModel

Todo modelo con datos financieros hereda de este. NUNCA se borra físicamente.

```python
# booking/models/base.py
from django.db import models
from django.utils import timezone


class SoftDeleteManager(models.Manager):
    def get_queryset(self):
        return super().get_queryset().filter(deleted_at__isnull=True)


class SoftDeleteModel(models.Model):
    deleted_at = models.DateTimeField(null=True, blank=True, db_index=True)

    objects = SoftDeleteManager()
    all_objects = models.Manager()  # incluye borrados — usar en admin y auditoría

    def delete(self, *args, **kwargs):
        self.deleted_at = timezone.now()
        self.save(update_fields=['deleted_at'])

    def hard_delete(self, *args, **kwargs):
        """Solo para tests y limpieza de datos de prueba."""
        super().delete(*args, **kwargs)

    class Meta:
        abstract = True
```

---

## Modelos existentes — campos clave

### Proyecto

```python
class Proyecto(SoftDeleteModel):
    nombre         = models.CharField(max_length=200)
    slug           = models.SlugField(unique=True)       # ← bug Bloque 0: autogenerar con sufijo
    descripcion    = models.TextField()
    owner          = models.ForeignKey(User, on_delete=models.CASCADE)
    owner_type     = models.CharField(max_length=10)     # 'INTERNAL' | 'EXTERNAL'

    # Tokens
    precio_token   = models.DecimalField(max_digits=12, decimal_places=2)
    tokens_totales = models.IntegerField(default=0)
    tokens_vendidos = models.IntegerField(default=0)     # ← SKIP en QA, hay que implementar

    # RWA
    gps_data       = models.JSONField(null=True, blank=True)
    legal_hash     = models.CharField(max_length=66, blank=True)
    spv_legal_name = models.CharField(max_length=200, blank=True)
    docs_manifest_hash = models.CharField(max_length=66, blank=True)
    venta_solo_drops = models.BooleanField(default=False)

    activo         = models.BooleanField(default=True)
    created_at     = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [
            models.Index(fields=['owner_type', 'activo']),
            models.Index(fields=['slug']),
        ]
```

### Reserva (ATENCIÓN: eliminar campos FirmaVirtual en Bloque 0)

```python
class Reserva(SoftDeleteModel):
    user            = models.ForeignKey(User, on_delete=models.CASCADE)
    proyecto        = models.ForeignKey(Proyecto, on_delete=models.CASCADE)
    cantidad_tokens = models.IntegerField()
    total           = models.DecimalField(max_digits=12, decimal_places=2)
    estado_pago     = models.CharField(max_length=20)    # EstadoPago choices
    metodo_pago     = models.CharField(max_length=20)    # MetodoPago choices
    created_at      = models.DateTimeField(auto_now_add=True)

    # Pasarelas
    mp_payment_id   = models.CharField(max_length=100, blank=True, db_index=True)
    cryptomus_uuid  = models.CharField(max_length=100, blank=True, unique=True, null=True)
    kushki_token    = models.CharField(max_length=100, blank=True)

    # Blockchain (Fase 3)
    tx_hash         = models.CharField(max_length=66, blank=True)

    # ELIMINAR en Bloque 0:
    # firmavirtual_id, firmavirtual_url, firmavirtual_status,
    # firmavirtual_files_ids, contrato_firmado

    class Meta:
        indexes = [
            models.Index(fields=['user', 'estado_pago']),
            models.Index(fields=['mp_payment_id']),
            models.Index(fields=['cryptomus_uuid']),
        ]
```

### ProjectDrop

```python
class ProjectDrop(models.Model):
    proyecto        = models.ForeignKey(Proyecto, on_delete=models.CASCADE,
                                        related_name='drops')
    nombre          = models.CharField(max_length=100)   # "Drop 1", "Drop 2", "Drop 3"
    numero          = models.IntegerField()              # 1, 2, 3
    stock_total     = models.IntegerField()
    stock_disponible = models.IntegerField()
    precio_override = models.DecimalField(max_digits=12, decimal_places=2,
                                          null=True, blank=True)
    fecha_inicio    = models.DateTimeField()
    fecha_fin       = models.DateTimeField()
    activo          = models.BooleanField(default=False)

    class Meta:
        unique_together = [['proyecto', 'numero']]
        indexes = [models.Index(fields=['proyecto', 'activo'])]
```

### UserProfile

```python
class UserProfile(models.Model):
    user              = models.OneToOneField(User, on_delete=models.CASCADE)
    kyc_tier          = models.IntegerField(default=1)   # 1=Bronze 2=Silver 3=Gold 4=Black
    investment_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0)
    wallet_address    = models.CharField(max_length=42, blank=True)  # Ethereum/Polygon
    kyc_verificado_en = models.DateTimeField(null=True, blank=True)
    didit_session_id  = models.CharField(max_length=100, blank=True)
    # NOTA: campo limit_usd esperado por QA-02-E → agregar o ajustar QA
```

---

## Modelos NUEVOS — crear en Semana 2

### CreditBalance

```python
# booking/models/creditos.py
from decimal import Decimal
from django.db import models
from django.contrib.auth.models import User
from django.utils import timezone
from .base import SoftDeleteModel


class CreditBalance(models.Model):
    """Un registro por usuario. Saldo actual de créditos RWA."""
    user        = models.OneToOneField(User, on_delete=models.CASCADE,
                                       related_name='credit_balance')
    balance_usd = models.DecimalField(max_digits=10, decimal_places=2,
                                      default=Decimal('0.00'))
    tier        = models.IntegerField(default=1)         # 1=Bronze 2=Silver 3=Gold 4=Black
    expires_at  = models.DateTimeField()                 # 12 meses desde primera emisión
    extended    = models.BooleanField(default=False)     # True si ya usó la extensión a 18m

    class Meta:
        indexes = [models.Index(fields=['expires_at', 'tier'])]

    def __str__(self):
        return f"{self.user.email} | ${self.balance_usd} | T{self.tier}"
```

### CreditTransaction

```python
class CreditTransaction(SoftDeleteModel):
    """Registro inmutable de cada movimiento de créditos."""
    TIPOS = [
        ('COMPRA',    'Compra de créditos'),
        ('USO',       'Uso en checkout'),
        ('EXPIRACION','Expiración automática'),
        ('EXTENSION', 'Extensión a 18 meses'),
        ('AJUSTE',    'Ajuste manual por Joan'),
    ]
    user       = models.ForeignKey(User, on_delete=models.CASCADE,
                                   related_name='credit_transactions')
    tipo       = models.CharField(max_length=20, choices=TIPOS)
    monto_usd  = models.DecimalField(max_digits=10, decimal_places=2)
    reserva    = models.ForeignKey('Reserva', null=True, blank=True,
                                   on_delete=models.SET_NULL)
    descripcion = models.CharField(max_length=255)
    created_at  = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'created_at'])]
        ordering = ['-created_at']
```

### TierConfig

```python
class TierConfig(models.Model):
    """Configurable desde admin. Cambios no requieren deploy."""
    tier                   = models.IntegerField(unique=True)   # 1-4
    nombre                 = models.CharField(max_length=50)    # Bronze/Silver/Gold/Black
    cap_creditos_usd       = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_fees_pct     = models.DecimalField(max_digits=5, decimal_places=2)
    descuento_creditos_pct = models.DecimalField(max_digits=5, decimal_places=2)
    kyc_requerido          = models.CharField(max_length=20)    # lite/standard/edd

    # Fixtures iniciales (Semana 2):
    # T1 Bronze:  cap=1000,  fees=7.5,  creditos=10, kyc=lite
    # T2 Silver:  cap=5000,  fees=15,   creditos=20, kyc=standard
    # T3 Gold:    cap=15000, fees=22.5, creditos=30, kyc=standard
    # T4 Black:   cap=25000, fees=31.5, creditos=40, kyc=edd

    def __str__(self):
        return f"T{self.tier} {self.nombre}"
```

### FeeConfig

```python
class FeeConfig(models.Model):
    """Fee schedule configurable desde admin."""
    TIPOS = [
        ('LISTING',     'Listing/Originación'),
        ('TRANSACCION', 'Transacción'),
        ('ADMIN',       'Administración anual'),
        ('CASHOUT',     'Retiro/Cash-out'),
        ('PREMIUM',     'Servicio premium'),
    ]
    tipo               = models.CharField(max_length=20, choices=TIPOS, unique=True)
    porcentaje         = models.DecimalField(max_digits=5, decimal_places=2)
    monto_minimo_usd   = models.DecimalField(max_digits=10, decimal_places=2, default=0)
    descripcion        = models.CharField(max_length=255)
    activo             = models.BooleanField(default=True)

    # Fixtures iniciales:
    # LISTING:     1.5%, mínimo $500 USD
    # TRANSACCION: 1.0%, mínimo $0
    # ADMIN:       1.0%, mínimo $0 (anual prorrateado)
    # CASHOUT:     1.0%, mínimo $0
    # PREMIUM:     0.0%, mínimo $10 USD
```

### AuditLog

```python
class AuditLog(models.Model):
    """Inmutable: no hay update ni delete. Registro de todo lo importante."""
    user         = models.ForeignKey(User, on_delete=models.SET_NULL,
                                     null=True, related_name='audit_logs')
    accion       = models.CharField(max_length=100)    # 'reserva.confirmada', 'kyc.aprobado'
    objeto_tipo  = models.CharField(max_length=50)     # 'Reserva', 'UserProfile'
    objeto_id    = models.IntegerField(null=True)
    datos_antes  = models.JSONField(null=True)
    datos_despues = models.JSONField(null=True)
    ip_address   = models.GenericIPAddressField(null=True)
    user_agent   = models.CharField(max_length=500, blank=True)
    created_at   = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['-created_at']
        indexes  = [
            models.Index(fields=['accion', 'created_at']),
            models.Index(fields=['objeto_tipo', 'objeto_id']),
        ]

    @classmethod
    def registrar(cls, accion: str, objeto=None, user=None,
                  datos_antes=None, datos_despues=None, request=None):
        """Factory method para crear logs sin boilerplate."""
        return cls.objects.create(
            accion=accion,
            user=user or (request.user if request and request.user.is_authenticated else None),
            objeto_tipo=type(objeto).__name__ if objeto else '',
            objeto_id=objeto.pk if objeto else None,
            datos_antes=datos_antes,
            datos_despues=datos_despues,
            ip_address=_get_client_ip(request) if request else None,
        )
```

### FraccionadorProfile

```python
class FraccionadorProfile(models.Model):
    user          = models.OneToOneField(User, on_delete=models.CASCADE,
                                         related_name='fraccionador_profile')
    KYB_ESTADOS = [
        ('PENDIENTE',   'Pendiente revisión'),
        ('EN_REVISION', 'En revisión'),
        ('APROBADO',    'Aprobado'),
        ('RECHAZADO',   'Rechazado'),
        ('MAS_DOCS',    'Requiere más documentos'),
    ]
    TIPOS = [('PERSONA', 'Persona natural'), ('EMPRESA', 'Empresa')]

    kyb_estado    = models.CharField(max_length=20, choices=KYB_ESTADOS, default='PENDIENTE')
    tipo          = models.CharField(max_length=10, choices=TIPOS, default='PERSONA')
    razon_social  = models.CharField(max_length=200, blank=True)
    rut_empresa   = models.CharField(max_length=12, blank=True)

    # Documentos (Cloudflare R2)
    doc_dominio_vigente = models.FileField(upload_to='kyb/dominios/', null=True, blank=True)
    doc_escritura       = models.FileField(upload_to='kyb/escrituras/', null=True, blank=True)
    doc_tasacion        = models.FileField(upload_to='kyb/tasaciones/', null=True, blank=True)

    # Financiero
    tokens_reserve_pct  = models.DecimalField(max_digits=5, decimal_places=2, default=20)
    banco               = models.CharField(max_length=100, blank=True)
    cuenta_bancaria     = models.CharField(max_length=50, blank=True)
    tipo_cuenta         = models.CharField(max_length=20, blank=True)

    kyb_revisado_por    = models.ForeignKey(User, null=True, blank=True,
                                            on_delete=models.SET_NULL,
                                            related_name='kyb_revisiones')
    kyb_fecha_aprobacion = models.DateTimeField(null=True, blank=True)
    kyb_notas           = models.TextField(blank=True)   # notas internas Joan

    class Meta:
        indexes = [models.Index(fields=['kyb_estado'])]
```

---

## constants.py — actualizar en Bloque 0

```python
# booking/constants.py

from django.db import models


class EstadoPago(models.TextChoices):
    PENDIENTE   = 'PENDIENTE',    'Pendiente'
    EN_REVISION = 'EN_REVISION',  'En revisión'
    CONFIRMADO  = 'CONFIRMADO',   'Confirmado'
    RECHAZADO   = 'RECHAZADO',    'Rechazado'
    FALLIDO     = 'FALLIDO',      'Fallido'
    REEMBOLSADO = 'REEMBOLSADO',  'Reembolsado'


class MetodoPago(models.TextChoices):
    MP      = 'MP',      'MercadoPago'
    CRYPTO  = 'CRYPTO',  'Cryptomus'
    KUSHKI  = 'KUSHKI',  'Kushki'
    CREDITO = 'CREDITO', 'Créditos RWA'


KYC_LIMITS_USD = {
    1: 1_000,    # Bronze
    2: 5_000,    # Silver
    3: 15_000,   # Gold
    4: 100_000,  # Black VIP
}

TIER_NOMBRES = {
    1: 'Bronze',
    2: 'Silver',
    3: 'Gold',
    4: 'Black VIP',
}

TIER_DESCUENTO_CREDITOS = {
    1: 10,
    2: 20,
    3: 30,
    4: 40,
}
```

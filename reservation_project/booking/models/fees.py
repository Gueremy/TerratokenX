from decimal import Decimal

from django.db import models


class TierConfig(models.Model):
    """Configuración de tiers. Editable desde admin — cambios no requieren deploy."""
    tier = models.IntegerField(unique=True)     # 1-4
    nombre = models.CharField(max_length=50)    # Bronze/Silver/Gold/Black
    cap_creditos_usd = models.DecimalField(max_digits=10, decimal_places=2)
    descuento_fees_pct = models.DecimalField(max_digits=5, decimal_places=2)
    descuento_creditos_pct = models.DecimalField(max_digits=5, decimal_places=2)
    kyc_requerido = models.CharField(max_length=20)  # lite/standard/edd

    class Meta:
        ordering = ['tier']

    def __str__(self):
        return f"T{self.tier} {self.nombre}"


class FeeConfig(models.Model):
    """Fee schedule configurable desde admin."""
    TIPOS = [
        ('LISTING', 'Listing/Originación'),
        ('TRANSACCION', 'Transacción'),
        ('ADMIN', 'Administración anual'),
        ('CASHOUT', 'Retiro/Cash-out'),
        ('PREMIUM', 'Servicio premium'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPOS, unique=True)
    porcentaje = models.DecimalField(max_digits=5, decimal_places=2)
    monto_minimo_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    descripcion = models.CharField(max_length=255)
    activo = models.BooleanField(default=True)

    def __str__(self):
        return f"{self.tipo} ({self.porcentaje}%)"

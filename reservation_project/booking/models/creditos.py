from decimal import Decimal

from django.db import models

from .base import SoftDeleteModel


class CreditBalance(models.Model):
    """Un registro por usuario. Saldo actual de créditos RWA."""
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='credit_balance')
    balance_usd = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal('0.00'))
    tier = models.IntegerField(default=1)       # 1=Bronze 2=Silver 3=Gold 4=Black
    expires_at = models.DateTimeField()         # 12 meses desde primera emisión
    extended = models.BooleanField(default=False)  # True si ya usó la extensión a 18m

    class Meta:
        indexes = [models.Index(fields=['expires_at', 'tier'])]

    def __str__(self):
        return f"{self.user.email} | ${self.balance_usd} | T{self.tier}"


class CreditTransaction(SoftDeleteModel):
    """Registro inmutable de cada movimiento de créditos."""
    TIPOS = [
        ('COMPRA', 'Compra de créditos'),
        ('USO', 'Uso en checkout'),
        ('EXPIRACION', 'Expiración automática'),
        ('EXTENSION', 'Extensión a 18 meses'),
        ('DEVOLUCION', 'Devolución por pago fallido'),
        ('AJUSTE', 'Ajuste manual por Joan'),
    ]
    user = models.ForeignKey('auth.User', on_delete=models.CASCADE, related_name='credit_transactions')
    tipo = models.CharField(max_length=20, choices=TIPOS)
    monto_usd = models.DecimalField(max_digits=10, decimal_places=2)
    reserva = models.ForeignKey('booking.Reserva', null=True, blank=True, on_delete=models.SET_NULL)
    descripcion = models.CharField(max_length=255)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        indexes = [models.Index(fields=['user', 'created_at'])]
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.user.email} | {self.tipo} | ${self.monto_usd}"

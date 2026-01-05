# En tu archivo models.py

import uuid
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

# Modelo para los cupones de descuento
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.PositiveIntegerField(help_text="Porcentaje de descuento (e.g., 10 para 10%)")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField()
    valid_to = models.DateField()

    def __str__(self):
        return self.code

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_to

class Reserva(models.Model):
    # --- Campos existentes ---
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    # fecha, dias, espacio_techado REMOVED
    pagado = models.BooleanField(default=False)
    created_at = models.DateTimeField(auto_now_add=True)  # Added timestamp as requested
    updated_at = models.DateTimeField(auto_now=True)

    # Campos para pago Crypto (DIY Flow)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, help_text="Monto exacto esperado en crypto")
    crypto_currency = models.CharField(max_length=10, null=True, blank=True, help_text="Ej: ETH, BTC")
    crypto_address = models.CharField(max_length=255, null=True, blank=True, help_text="Dirección de depósito asignada")
    payment_window_start = models.DateTimeField(null=True, blank=True, help_text="Inicio de la ventana de espera del pago")

    # --- Nuevos campos ---
    cantidad_tokens = models.PositiveIntegerField("Cantidad de Tokens", default=1)
    numero_reserva = models.CharField(max_length=10, editable=False, unique=True, blank=True)
    total = models.DecimalField("Total", max_digits=10, decimal_places=2, default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)

    PAYMENT_METHOD_CHOICES = [
        ('MP', 'Mercado Pago'),
        ('CRYPTO', 'CryptoMarket'),
    ]
    metodo_pago = models.CharField(
        max_length=10,
        choices=PAYMENT_METHOD_CHOICES,
        default='MP',
        verbose_name="Método de Pago"
    )

    def save(self, *args, **kwargs):
        # Generar número de reserva único si es una nueva reserva
        if not self.pk:
            self.numero_reserva = uuid.uuid4().hex[:8].upper()
        
        # Obtener la configuración de precios
        config = Configuracion.load()

        # Calcular el total: Precio Base * Cantidad
        self.total = config.precio_base_token * self.cantidad_tokens
        
        # Aplicar descuento si hay un cupón válido
        if self.coupon and self.coupon.is_valid():
            descuento = (self.total * self.coupon.discount_percentage) / 100
            self.total -= descuento

        # Aplicar comisión del 4% si es Mercado Pago
        if self.metodo_pago == 'MP':
            from decimal import Decimal
            # Convertir a Decimal para evitar errores de tipo float
            self.total = float(self.total) * 1.04

        super().save(*args, **kwargs)

    def __str__(self):
        return f"{self.nombre} - {self.numero_reserva}"

class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"

class Configuracion(models.Model):
    precio_base_token = models.PositiveIntegerField(default=100000, verbose_name="Precio Base Token")

    def __str__(self):
        return "Configuración de Precios"

    class Meta:
        verbose_name = "Configuración"
        verbose_name_plural = "Configuraciones"

    @classmethod
    def load(cls):
        """Carga la instancia única, creándola con valores por defecto si no existe."""
        obj, created = cls.objects.get_or_create(pk=1)
        return obj

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
    # --- Estados de Pago ---
    ESTADO_PENDIENTE = 'PENDIENTE'
    ESTADO_EN_REVISION = 'EN_REVISION'
    ESTADO_CONFIRMADO = 'CONFIRMADO'
    
    ESTADO_PAGO_CHOICES = [
        (ESTADO_PENDIENTE, 'Pendiente'),
        (ESTADO_EN_REVISION, 'En Revisión'),
        (ESTADO_CONFIRMADO, 'Confirmado'),
    ]

    # --- Campos existentes ---
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    telefono = models.CharField(max_length=20)
    direccion = models.CharField(max_length=200)
    
    # Nuevo campo de estado de pago (reemplaza pagado boolean)
    estado_pago = models.CharField(
        max_length=15,
        choices=ESTADO_PAGO_CHOICES,
        default=ESTADO_PENDIENTE,
        verbose_name="Estado de Pago"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos para pago Crypto (DIY Flow)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, help_text="Monto exacto esperado en crypto")
    crypto_currency = models.CharField(max_length=10, null=True, blank=True, help_text="Ej: ETH, BTC")
    crypto_address = models.CharField(max_length=255, null=True, blank=True, help_text="Dirección de depósito asignada")
    payment_window_start = models.DateTimeField(null=True, blank=True, help_text="Inicio de la ventana de espera del pago")
    
    # --- Datos para Contrato Legal (FirmaVirtual) ---
    rut = models.CharField("RUT Firmante", max_length=20, blank=True, null=True, help_text="RUT de quien firma (Persona o Rep. Legal)")
    telefono = models.CharField(max_length=20, blank=True, null=True, help_text="Fundamental para FirmaVirtual")
    
    # Datos para Persona Jurídica
    es_empresa = models.BooleanField(default=False, verbose_name="¿Es Persona Jurídica?")
    razon_social = models.CharField(max_length=200, blank=True, null=True, help_text="Solo si es empresa")
    rut_empresa = models.CharField(max_length=20, blank=True, null=True, help_text="RUT de la empresa")
    cargo_representante = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Gerente General")

    # Integración FirmaVirtual (Tracking)
    firmavirtual_id = models.CharField(max_length=100, blank=True, null=True, help_text="ID del trámite en FV (request_id)")
    firmavirtual_url = models.URLField(max_length=500, blank=True, null=True, help_text="Link para firmar")
    firmavirtual_status = models.CharField(max_length=50, default='pending', help_text="Estado: pending, signed, rejected")
    firmavirtual_files_ids = models.JSONField(default=list, blank=True, help_text="IDs de archivos asociados")
    
    # Archivo Final
    contrato_firmado = models.FileField(upload_to='contratos_firmados/', blank=True, null=True)

    # --- Nuevos campos (Tokens) ---
    cantidad_tokens = models.PositiveIntegerField("Cantidad de Tokens", default=1)
    numero_reserva = models.CharField(max_length=10, editable=False, unique=True, blank=True)
    total = models.PositiveIntegerField("Total", default=0)
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    # Nuevo: Vinculación con Proyecto
    proyecto = models.ForeignKey('Proyecto', on_delete=models.CASCADE, null=True, blank=True, related_name='reserva_set')

    PAYMENT_METHOD_CHOICES = [
        ('MP', 'Mercado Pago'),
        ('CRYPTO', 'CryptoMarket'),
        ('CRYPTO_MANUAL', 'Crypto (Manual)'),
    ]
    metodo_pago = models.CharField(
        max_length=15,
        choices=PAYMENT_METHOD_CHOICES,
        default='MP',
        verbose_name="Método de Pago"
    )

    # Propiedad computada para compatibilidad con código existente
    @property
    def pagado(self):
        """Retorna True si el pago está confirmado (para compatibilidad)."""
        return self.estado_pago == self.ESTADO_CONFIRMADO
    
    @pagado.setter
    def pagado(self, value):
        """Permite asignar pagado=True/False para compatibilidad."""
        if value:
            self.estado_pago = self.ESTADO_CONFIRMADO
        else:
            self.estado_pago = self.ESTADO_PENDIENTE

    def save(self, *args, **kwargs):
        # Generar número de reserva único si es una nueva reserva
        if not self.pk:
            self.numero_reserva = uuid.uuid4().hex[:8].upper()
        
        # Obtener la configuración de precios
        config = Configuracion.load()

        # Calcular el total: Precio Base (del proyecto o configuración global) * Cantidad
        if self.proyecto:
            precio_unitario = self.proyecto.precio_token
        else:
            precio_unitario = config.precio_base_token
            
        self.total = precio_unitario * self.cantidad_tokens
        
        # Aplicar descuento si hay un cupón válido
        if self.coupon and self.coupon.is_valid():
            descuento = (self.total * self.coupon.discount_percentage) / 100
            self.total -= descuento

        # Aplicar comisión del 4% si es Mercado Pago
        if self.metodo_pago == 'MP':
            from decimal import Decimal
            # Convertir a Decimal para evitar errores de tipo float
            self.total = float(self.total) * 1.0319

        # Detectar si el estado cambió a CONFIRMADO para disparar FirmaVirtual
        trigger_firmavirtual = False
        if self.pk:
            # Si es una actualización, verificar si el estado cambió
            try:
                old_instance = Reserva.objects.get(pk=self.pk)
                if old_instance.estado_pago != self.ESTADO_CONFIRMADO and self.estado_pago == self.ESTADO_CONFIRMADO:
                    trigger_firmavirtual = True
            except Reserva.DoesNotExist:
                pass

        super().save(*args, **kwargs)
        
        # Después de guardar, si toca disparar acciones por confirmación de pago
        if trigger_firmavirtual:
            # 1. Enviar email de bienvenida al cliente
            self._send_welcome_email()
            
            # 2. Disparar FirmaVirtual si no tiene contrato ya
            if not self.firmavirtual_id:
                self._trigger_firmavirtual_contract()

    def _send_welcome_email(self):
        """
        Envía email de bienvenida cuando el pago es confirmado.
        """
        import threading
        from django.core.mail import send_mail
        from django.template.loader import render_to_string
        from django.conf import settings
        
        def send_email():
            try:
                context = {'reserva': self}
                html_message = render_to_string('booking/emails/payment_confirmed_welcome.html', context)
                
                send_mail(
                    subject=f'🎉 ¡Bienvenido a TerraTokenX! - Reserva #{self.numero_reserva}',
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[self.correo],
                    fail_silently=False,
                    html_message=html_message,
                )
                print(f"📧 Email de bienvenida enviado a {self.correo}")
            except Exception as e:
                print(f"❌ Error enviando email de bienvenida: {e}")
        
        # Ejecutar en hilo separado
        email_thread = threading.Thread(target=send_email)
        email_thread.start()

    def _trigger_firmavirtual_contract(self):
        """
        Dispara la creación del contrato en FirmaVirtual.
        Se ejecuta automáticamente cuando el pago pasa a CONFIRMADO.
        """
        try:
            from booking.services.firmavirtual import FirmaVirtualService
            service = FirmaVirtualService()
            result = service.create_contract_request(self)
            
            if 'error' not in result and result.get('status') == 'success':
                # Guardar el ID del trámite - está en message.contract.sContractID
                contract_data = result.get('message', {}).get('contract', {})
                fv_id = contract_data.get('sContractID')
                if fv_id:
                    self.firmavirtual_id = str(fv_id)
                    self.firmavirtual_status = 'sent'
                    self.save(update_fields=['firmavirtual_id', 'firmavirtual_status'])
                print(f"FirmaVirtual: Contrato creado para reserva {self.numero_reserva} - ID: {fv_id}")
            else:
                print(f"FirmaVirtual Error para reserva {self.numero_reserva}: {result.get('error')}")
        except Exception as e:
            print(f"Excepción FirmaVirtual para reserva {self.numero_reserva}: {str(e)}")

    def __str__(self):
        return f"{self.nombre} - {self.numero_reserva}"

class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"

class Proyecto(models.Model):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, help_text="URL amigable (ej: refugio-patagonia)")
    descripcion = models.TextField(blank=True)
    ubicacion = models.CharField(max_length=200, default="Patagonia Chilena")
    
    # Imagenes
    imagen_portada = models.ImageField(upload_to='proyectos/', null=True, blank=True)
    imagen_portada_url = models.URLField(blank=True, null=True, help_text="URL externa de la imagen (opcional, ahorra espacio)")
    video_url = models.URLField(blank=True, null=True, help_text="URL del video del proyecto (YouTube, Vimeo, etc.)")
    
    # Tokenomics
    precio_token = models.PositiveIntegerField(default=100, help_text="Precio por token en USD")
    tokens_totales = models.PositiveIntegerField(default=1500)
    rentabilidad_estimada = models.CharField(max_length=50, default="12-18% Anual")
    
    # Estado
    activo = models.BooleanField(default=True, help_text="Visible en la web")
    financiamiento_activo = models.BooleanField(default=True, help_text="Permite comprar tokens")
    
    created_at = models.DateTimeField(auto_now_add=True)

    # Tipo de proyecto (Terreno, Departamento, Casa, Campo, Negocio)
    TIPO_CHOICES = [
        ('Terreno', 'Terreno'),
        ('Departamento', 'Departamento'),
        ('Casa', 'Casa'),
        ('Campo', 'Campo'),
        ('Negocio', 'Negocio'),
    ]
    tipo = models.CharField(max_length=20, choices=TIPO_CHOICES, default='Terreno')

    # Estado del proyecto (Activo, Próximamente, Vendido)
    ESTADO_CHOICES = [
        ('Activo', 'Activo'),
        ('Proximamente', 'Próximamente'),
        ('Vendido', 'Vendido'),
    ]
    estado = models.CharField(max_length=20, choices=ESTADO_CHOICES, default='Activo')

    # Enlace a la página oficial del proyecto (para botón "Ir a web")
    pagina_oficial_url = models.URLField(blank=True, null=True, help_text='Enlace a la página oficial del proyecto')

    def save(self, *args, **kwargs):
        # Auto-fix Google Drive links
        if self.imagen_portada_url and 'drive.google.com' in self.imagen_portada_url:
            import re
            # Match formats like /file/d/[ID]/view or /open?id=[ID]
            match = re.search(r'/file/d/([^/?#]+)', self.imagen_portada_url)
            if not match:
                match = re.search(r'[?&]id=([^&#]+)', self.imagen_portada_url)
            
            if match:
                file_id = match.group(1)
                # Usar lh3.googleusercontent.com es más fiable para imágenes directas (Content-Type correcto)
                self.imagen_portada_url = f"https://lh3.googleusercontent.com/d/{file_id}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return self.nombre

    @property
    def tokens_vendidos(self):
        # Calcular tokens vendidos dinámicamente
        return self.reserva_set.filter(estado_pago='CONFIRMADO').aggregate(
            total=models.Sum('cantidad_tokens')
        )['total'] or 0

    @property
    def tokens_disponibles(self):
        return self.tokens_totales - self.tokens_vendidos

    @property
    def porcentaje_vendido(self):
        if self.tokens_totales > 0:
            return round((self.tokens_vendidos / self.tokens_totales) * 100, 2)
        return 0

# Modelo para la galería de imágenes del proyecto
class ProyectoImagen(models.Model):
    proyecto = models.ForeignKey('Proyecto', related_name='imagenes', on_delete=models.CASCADE)
    imagen = models.ImageField(upload_to='proyectos/galeria/', blank=True, null=True)
    imagen_url = models.URLField(blank=True, null=True, help_text="URL externa de la imagen")
    caption = models.CharField(max_length=200, blank=True)

    def save(self, *args, **kwargs):
        # Auto-fix Google Drive links
        if self.imagen_url and 'drive.google.com' in self.imagen_url:
            import re
            match = re.search(r'/file/d/([^/?#]+)', self.imagen_url)
            if not match:
                match = re.search(r'[?&]id=([^&#]+)', self.imagen_url)
            
            if match:
                file_id = match.group(1)
                self.imagen_url = f"https://lh3.googleusercontent.com/d/{file_id}"
        
        super().save(*args, **kwargs)

    def __str__(self):
        return f"Imagen de {self.proyecto.nombre}"


# Modelo para secciones/tabs personalizables del proyecto
class ProyectoSeccion(models.Model):
    """
    Secciones personalizables para cada proyecto (tabs como Resumen, Análisis, Números, etc.)
    Estas secciones se muestran en la landing page via API.
    """
    proyecto = models.ForeignKey('Proyecto', related_name='secciones', on_delete=models.CASCADE)
    nombre = models.CharField(max_length=100, help_text="Nombre del tab (ej: Resumen, Análisis, Números)")
    icono = models.CharField(max_length=50, blank=True, null=True, help_text="Emoji o nombre de icono (ej: 📊, description)")
    contenido = models.TextField(help_text="Contenido de la sección (puede ser HTML)")
    orden = models.PositiveIntegerField(default=0, help_text="Orden de aparición (menor = primero)")
    activo = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['orden', 'id']
        verbose_name = "Sección de Proyecto"
        verbose_name_plural = "Secciones de Proyecto"

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.nombre}"

class Configuracion(models.Model):
    precio_base_token = models.PositiveIntegerField(default=100, verbose_name="Precio Base Token (USD)")
    # Deprecado: tokens_totales se mueve a Proyecto
    tokens_totales = models.PositiveIntegerField(default=1500, verbose_name="Tokens Totales del Proyecto (Deprecado)")

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


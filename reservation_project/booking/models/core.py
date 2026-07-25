# En tu archivo models.py

import logging
import uuid
from decimal import Decimal
from django.db import models
from django.core.exceptions import ValidationError
from django.utils import timezone

logger = logging.getLogger('booking')

from .. import validators  # noqa: E402
from ..constants import EstadoPago, MetodoPago  # noqa: E402
from .base import SoftDeleteModel  # noqa: E402

# Modelo para los cupones de descuento
class Coupon(models.Model):
    code = models.CharField(max_length=50, unique=True)
    discount_percentage = models.PositiveIntegerField(help_text="Porcentaje de descuento (e.g., 10 para 10%)")
    is_active = models.BooleanField(default=True)
    valid_from = models.DateField(default=timezone.localdate)
    valid_to = models.DateField()

    def __str__(self):
        return self.code

    def is_valid(self):
        today = timezone.now().date()
        return self.is_active and self.valid_from <= today <= self.valid_to

class Reserva(SoftDeleteModel):
    # --- Estados de Pago (aliases de compatibilidad sobre constants.EstadoPago) ---
    ESTADO_PENDIENTE = EstadoPago.PENDIENTE
    ESTADO_EN_REVISION = EstadoPago.EN_REVISION
    ESTADO_CONFIRMADO = EstadoPago.CONFIRMADO
    ESTADO_RECHAZADO = EstadoPago.RECHAZADO
    ESTADO_FALLIDO = EstadoPago.FALLIDO
    ESTADO_REEMBOLSADO = EstadoPago.REEMBOLSADO

    # --- Campos existentes ---
    nombre = models.CharField(max_length=100)
    correo = models.EmailField()
    direccion = models.CharField(max_length=200, blank=True, null=True)

    # Nuevo campo de estado de pago (reemplaza pagado boolean)
    estado_pago = models.CharField(
        max_length=15,
        choices=EstadoPago.choices,
        default=EstadoPago.PENDIENTE,
        verbose_name="Estado de Pago"
    )
    
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    # Campos para pago Crypto (DIY Flow)
    crypto_amount = models.DecimalField(max_digits=20, decimal_places=8, null=True, blank=True, help_text="Monto exacto esperado en crypto")
    crypto_currency = models.CharField(max_length=10, null=True, blank=True, help_text="Ej: ETH, BTC")
    crypto_address = models.CharField(max_length=255, null=True, blank=True, help_text="Dirección de depósito asignada")
    payment_window_start = models.DateTimeField(null=True, blank=True, help_text="Inicio de la ventana de espera del pago")
    
    # --- Datos legales del comprador ---
    rut = models.CharField("RUT", max_length=20, blank=True, null=True, help_text="RUT del comprador (Persona o Rep. Legal)")
    telefono = models.CharField(max_length=20, blank=True, null=True)

    # Datos para Persona Jurídica
    es_empresa = models.BooleanField(default=False, verbose_name="¿Es Persona Jurídica?")
    razon_social = models.CharField(max_length=200, blank=True, null=True, help_text="Solo si es empresa")
    rut_empresa = models.CharField(max_length=20, blank=True, null=True, help_text="RUT de la empresa")
    cargo_representante = models.CharField(max_length=100, blank=True, null=True, help_text="Ej: Gerente General")

    # --- Nuevos campos (Tokens) ---
    cantidad_tokens = models.PositiveIntegerField("Cantidad de Tokens", default=1)
    numero_reserva = models.CharField(max_length=10, editable=False, unique=True, blank=True)
    total = models.DecimalField("Total", max_digits=12, decimal_places=2, default=Decimal('0.00'))
    coupon = models.ForeignKey(Coupon, on_delete=models.SET_NULL, null=True, blank=True)
    # Nuevo: Vinculación con Proyecto
    proyecto = models.ForeignKey('Proyecto', on_delete=models.CASCADE, null=True, blank=True, related_name='reserva_set')
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reserva_set')

    metodo_pago = models.CharField(
        max_length=15,
        choices=MetodoPago.choices,
        default=MetodoPago.MP,
        verbose_name="Método de Pago"
    )

    # --- Referencias de pasarelas de pago ---
    mp_payment_id = models.CharField(max_length=100, blank=True, db_index=True, help_text="ID de pago en MercadoPago")
    cryptomus_uuid = models.CharField(max_length=100, blank=True, null=True, unique=True, help_text="UUID del invoice en Cryptomus")
    kushki_token = models.CharField(max_length=100, blank=True, help_text="Token de transacción Kushki")

    # Blockchain (Fase 3)
    tx_hash = models.CharField(max_length=66, blank=True, help_text="Hash de la transacción de mint")

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
        
        # El total se recalcula salvo que un service lo haya fijado explícitamente
        # (ej: compra vía Drop con precio_override — ver services.crear_reserva_pendiente)
        if not getattr(self, '_total_manual', False):
            # Obtener la configuración de precios
            config = Configuracion.load()

            # Calcular el total: Precio Base (del proyecto o configuración global) * Cantidad
            if self.proyecto:
                precio_unitario = self.proyecto.precio_token
            else:
                precio_unitario = config.precio_base_token

            self.total = Decimal(precio_unitario) * self.cantidad_tokens

            # Aplicar descuento si hay un cupón válido
            if self.coupon and self.coupon.is_valid():
                descuento = (self.total * self.coupon.discount_percentage) / Decimal('100')
                self.total -= descuento

            # No aplicar comisión extra (a petición del usuario)
            self.total = self.total.quantize(Decimal('0.01'))

        # Detectar si el estado cambió a CONFIRMADO para disparar acciones post-pago
        recien_confirmada = False
        if self.pk:
            # Si es una actualización, verificar si el estado cambió
            try:
                old_instance = Reserva.objects.get(pk=self.pk)
                # Una reserva CONFIRMADA no puede volver a PENDIENTE (protección de estado)
                if (old_instance.estado_pago == self.ESTADO_CONFIRMADO
                        and self.estado_pago == self.ESTADO_PENDIENTE):
                    raise ValidationError(
                        "Una reserva CONFIRMADA no puede volver a estado PENDIENTE."
                    )
                if old_instance.estado_pago != self.ESTADO_CONFIRMADO and self.estado_pago == self.ESTADO_CONFIRMADO:
                    recien_confirmada = True
            except Reserva.DoesNotExist:
                pass

        super().save(*args, **kwargs)

        # Después de guardar, si toca disparar acciones por confirmación de pago
        if recien_confirmada:
            # 1. Actualizar contadores materializados (tokens vendidos e inversión acumulada)
            if self.proyecto_id:
                Proyecto.objects.filter(pk=self.proyecto_id).update(
                    tokens_vendidos=models.F('tokens_vendidos') + self.cantidad_tokens
                )
            if self.user_id:
                UserProfile.objects.filter(user_id=self.user_id).update(
                    investment_total_usd=models.F('investment_total_usd') + self.total
                )

            # 2. Enviar email de bienvenida al cliente
            self._send_welcome_email()

            # 3. Crear cuenta de usuario si no existe
            self._create_user_account()

    def _create_user_account(self):
        """
        Crea una cuenta de usuario de Django para el inversor si no existe.
        """
        from django.contrib.auth.models import User
        if not User.objects.filter(email=self.correo).exists():
            # Generar username basado en correo o nombre
            username = self.correo.split('@')[0]
            # Asegurar unicidad de username
            original_username = username
            counter = 1
            while User.objects.filter(username=username).exists():
                username = f"{original_username}{counter}"
                counter += 1
            
            # Crear usuario con password temporal (pueden recuperarla después)
            user = User.objects.create_user(
                username=username,
                email=self.correo,
                first_name=self.nombre.split(' ')[0] if ' ' in self.nombre else self.nombre,
                last_name=' '.join(self.nombre.split(' ')[1:]) if ' ' in self.nombre else ''
            )
            self.user = user
            self.save(update_fields=['user'])
            logger.info("Usuario creado automaticamente: %s (%s)", user.username, self.correo)
            return user
        user = User.objects.get(email=self.correo)
        self.user = user
        self.save(update_fields=['user'])
        return user

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
                # Recargar el objeto de la base de datos para asegurar datos frescos
                from booking.integrations.resend import _enviar
                from booking.models import Reserva
                reserva_actual = Reserva.objects.get(pk=self.pk)

                context = {'reserva': reserva_actual}
                html_message = render_to_string('booking/emails/payment_confirmed_welcome.html', context)

                _enviar(
                    to=reserva_actual.correo,
                    subject=f'Bienvenido a TerraTokenX - Reserva #{reserva_actual.numero_reserva}',
                    html=html_message,
                )
            except Exception as e:
                logger.error("Error enviando email de bienvenida: %s", e)
        
        # Ejecutar en hilo separado
        email_thread = threading.Thread(target=send_email)
        email_thread.start()

    def __str__(self):
        return f"{self.nombre} - {self.numero_reserva}"

class DiaFeriado(models.Model):
    fecha = models.DateField(unique=True)
    descripcion = models.CharField(max_length=100, blank=True)

    def __str__(self):
        return f"{self.fecha} - {self.descripcion}"

class Proyecto(SoftDeleteModel):
    nombre = models.CharField(max_length=200)
    slug = models.SlugField(unique=True, blank=True, help_text="URL amigable (ej: refugio-patagonia). Se genera sola si se deja vacío.")
    descripcion = models.TextField(blank=True)
    ubicacion = models.CharField(max_length=200, default="Patagonia Chilena")
    
    # Imagenes
    imagen_portada = models.ImageField(upload_to=validators.ruta_proyectos, null=True, blank=True, validators=[validators.validar_imagen])
    imagen_portada_url = models.URLField(blank=True, null=True, help_text="URL externa de la imagen (opcional, ahorra espacio)")
    video_url = models.URLField(blank=True, null=True, help_text="URL del video del proyecto (YouTube, Vimeo, etc.)")
    
    # Tokenomics
    precio_token = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100.00'), help_text="Precio por token en USD")
    tokens_totales = models.PositiveIntegerField(default=1500)
    
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

    # --- Dueño del proyecto (fraccionador) ---
    OWNER_TYPE_CHOICES = [
        ('INTERNAL', 'Interno (Joan)'),
        ('EXTERNAL', 'Externo (Fraccionador)'),
    ]
    owner = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='proyectos')
    owner_type = models.CharField(max_length=10, choices=OWNER_TYPE_CHOICES, default='INTERNAL')

    # --- Datos RWA ---
    gps_data = models.JSONField(null=True, blank=True)
    legal_hash = models.CharField(max_length=66, blank=True)
    spv_legal_name = models.CharField(max_length=200, blank=True)
    docs_manifest_hash = models.CharField(max_length=66, blank=True)
    venta_solo_drops = models.BooleanField(default=False, help_text="Si está activo, solo se puede comprar con Drop activo")

    # Contador materializado (se actualiza en confirmar_reserva y con la task sync_tokens_vendidos)
    tokens_vendidos = models.PositiveIntegerField(default=0)

    def save(self, *args, **kwargs):
        # Autogenerar slug único a partir del nombre si no viene definido
        if not self.slug:
            from django.utils.text import slugify
            base_slug = slugify(self.nombre)[:45] or 'proyecto'
            slug = base_slug
            contador = 2
            while Proyecto.all_objects.filter(slug=slug).exclude(pk=self.pk).exists():
                slug = f"{base_slug}-{contador}"
                contador += 1
            self.slug = slug

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

    def calcular_tokens_vendidos(self):
        """Suma real de tokens en reservas confirmadas (para la task de sync)."""
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
    imagen = models.ImageField(upload_to=validators.ruta_proyectos_galeria, blank=True, null=True, validators=[validators.validar_imagen])
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

class ProyectoDocumento(models.Model):
    """
    Documentos del proyecto (Data Room)
    """
    proyecto = models.ForeignKey('Proyecto', related_name='documentos', on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    archivo = models.FileField(upload_to=validators.ruta_proyectos_documentos, validators=[validators.validar_archivo_kyc])
    es_publico = models.BooleanField(default=True, verbose_name="¿Es público?")
    requiere_nda = models.BooleanField(default=False, verbose_name="¿Requiere NDA?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.titulo}"

class Configuracion(models.Model):
    precio_base_token = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('100.00'), verbose_name="Precio Base Token (USD)")
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


class UserProfile(models.Model):
    user = models.OneToOneField('auth.User', on_delete=models.CASCADE, related_name='profile')
    rut = models.CharField(max_length=20, blank=True, null=True)
    telefono = models.CharField(max_length=20, blank=True, null=True)
    direccion = models.CharField(max_length=200, blank=True, null=True)
    
    # KYC Status
    KYC_PENDIENTE = 'PENDIENTE'
    KYC_EN_REVISION = 'REVISION'
    KYC_APROBADO = 'APROBADO'
    KYC_RECHAZADO = 'RECHAZADO'
    
    KYC_STATUS_CHOICES = [
        (KYC_PENDIENTE, 'Pendiente de Envío'),
        (KYC_EN_REVISION, 'En Revisión'),
        (KYC_APROBADO, 'Aprobado'),
        (KYC_RECHAZADO, 'Rechazado'),
    ]
    
    kyc_status = models.CharField(
        max_length=20,
        choices=KYC_STATUS_CHOICES,
        default=KYC_PENDIENTE
    )

    # --- Tiers y límites KYC (1=Bronze 2=Silver 3=Gold 4=Black) ---
    kyc_tier = models.IntegerField(default=1)
    investment_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=Decimal('0.00'))
    kyc_verificado_en = models.DateTimeField(null=True, blank=True)
    didit_session_id = models.CharField(max_length=100, blank=True)
    
    # KYC Documents
    documento_identidad_frontal = models.ImageField(upload_to=validators.ruta_kyc_documentos, blank=True, null=True, validators=[validators.validar_archivo_kyc])
    documento_identidad_reverso = models.ImageField(upload_to=validators.ruta_kyc_documentos, blank=True, null=True, validators=[validators.validar_archivo_kyc])
    selfie_verificacion = models.ImageField(upload_to=validators.ruta_kyc_selfies, blank=True, null=True, validators=[validators.validar_imagen])
    
    fecha_kyc = models.DateTimeField(null=True, blank=True)
    comentarios_admin = models.TextField(blank=True, null=True)
    
    wallet_address = models.CharField(max_length=100, blank=True, null=True, help_text="Dirección de billetera (Opcional)")

    def __str__(self):
        return f"Perfil de {self.user.username}"

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

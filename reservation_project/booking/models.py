# En tu archivo models.py

import uuid
from django.conf import settings
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
    direccion = models.CharField(max_length=200, blank=True, null=True)
    
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
    user = models.ForeignKey('auth.User', on_delete=models.SET_NULL, null=True, blank=True, related_name='reserva_set')
    
    # Trazabilidad: ¿En qué Drop se hizo esta compra?
    drop = models.ForeignKey(
        'ProjectDrop',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='reservas',
        help_text='Drop en el que se realizó esta compra (para auditoría y métricas).'
    )

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

        # No aplicar comisión extra (a petición del usuario)
        self.total = int(self.total)

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
            # --- KYC UPDATE (NUEVO) ---
            if self.user and hasattr(self.user, 'profile'):
                try:
                    self.user.profile.investment_total_usd += self.total
                    self.user.profile.save()
                    print(f"💰 KYC Updated: +${self.total} USD for {self.user.username}")
                except Exception as e:
                    print(f"⚠️ Error updating KYC total: {e}")

            # 1. Enviar email de bienvenida al cliente
            self._send_welcome_email()
            
            # 2. Crear cuenta de usuario si no existe
            self._create_user_account()
            
            # 3. Disparar FirmaVirtual si no tiene contrato ya
            if not self.firmavirtual_id:
                self._trigger_firmavirtual_contract()

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
            print(f"👤 Usuario creado automáticamente: {user.username} ({self.correo})")
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
                from booking.models import Reserva
                reserva_actual = Reserva.objects.get(pk=self.pk)
                
                context = {'reserva': reserva_actual}
                print(f"DEBUG EMAIL: numero_reserva={reserva_actual.numero_reserva}, nombre={reserva_actual.nombre}")
                
                html_message = render_to_string('booking/emails/payment_confirmed_welcome.html', context)
                
                # Debug: verificar si el template se renderizó
                if '{{ reserva' in html_message:
                    print("ERROR: Template NO se renderizó correctamente!")
                else:
                    print("DEBUG: Template renderizado OK")
                
                send_mail(
                    subject=f'🎉 ¡Bienvenido a TerraTokenX! - Reserva #{reserva_actual.numero_reserva}',
                    message='',
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[reserva_actual.correo],
                    fail_silently=False,
                    html_message=html_message,
                )
                print(f"📧 Email de bienvenida enviado a {reserva_actual.correo}")
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
    
    # =============================================
    # MARKETPLACE: Separación Interno vs Externo
    # =============================================
    OWNER_TYPE_CHOICES = [
        ('INTERNAL', 'Proyecto Interno (Premium)'),
        ('EXTERNAL', 'Proyecto Externo (Marketplace)'),
    ]
    owner_type = models.CharField(
        max_length=10,
        choices=OWNER_TYPE_CHOICES,
        default='INTERNAL',
        help_text='INTERNAL = Proyecto propio (Joan). EXTERNAL = Proyecto de un Fraccionador externo.'
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='proyectos_propios',
        help_text='Usuario dueño del proyecto (solo para proyectos EXTERNAL).'
    )

    # =============================================
    # COMPLIANCE: Estado de revisión del proyecto
    # =============================================
    COMPLIANCE_STATUS_CHOICES = [
        ('NONE', 'Sin revisión'),
        ('DRAFT', 'Borrador'),
        ('REVIEW', 'En Revisión'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]
    compliance_status = models.CharField(
        max_length=10,
        choices=COMPLIANCE_STATUS_CHOICES,
        default='NONE',
        help_text='Estado de revisión/compliance del proyecto.'
    )

    DOCS_STATUS_CHOICES = [
        ('MISSING', 'Documentos Faltantes'),
        ('PARTIAL', 'Documentación Parcial'),
        ('COMPLETE', 'Documentación Completa'),
    ]
    docs_status = models.CharField(
        max_length=10,
        choices=DOCS_STATUS_CHOICES,
        default='MISSING',
        help_text='Estado de la documentación legal del proyecto.'
    )
    
    # Documento de Propiedad (Obligatorio para revisión)
    archivo_propiedad = models.FileField(
        upload_to='proyectos/legal/',
        blank=True,
        null=True,
        help_text='Escritura o Certificado de Dominio Vigente para validar propiedad.'
    )

    # =============================================
    # METADATOS RWA (Pre-Blockchain)
    # =============================================
    gps_data = models.JSONField(
        blank=True,
        null=True,
        default=dict,
        help_text='Coordenadas GPS del activo. Ej: {"lat": -43.77, "lng": -71.69}'
    )
    spv_legal_name = models.CharField(
        max_length=200,
        blank=True,
        default='',
        help_text='Nombre legal del SPV/Sociedad dueña del activo (ej: Refugio Patagonia SpA).'
    )
    legal_hash = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text='Hash SHA-256 del paquete contractual/legal del proyecto.'
    )
    docs_manifest_hash = models.CharField(
        max_length=128,
        blank=True,
        default='',
        help_text='Hash SHA-256 del manifiesto de documentos (Due Diligence).'
    )
    data_room_url = models.URLField(
        blank=True,
        null=True,
        help_text='Enlace al Data Room del proyecto (Google Drive, Notion, etc.).'
    )

    # =============================================
    # CAMPOS ORIGINALES
    # =============================================
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
    
    # =============================================
    # DROPS: Control de venta por ventanas
    # =============================================
    venta_solo_drops = models.BooleanField(
        default=False,
        verbose_name='Venta solo vía Drops',
        help_text='Si está activado, solo se puede comprar cuando hay un Drop activo. Si no hay Drop abierto, el proyecto queda bloqueado.'
    )
    
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

class ProyectoDocumento(models.Model):
    """
    Documentos del proyecto (Data Room)
    """
    proyecto = models.ForeignKey('Proyecto', related_name='documentos', on_delete=models.CASCADE)
    titulo = models.CharField(max_length=200)
    archivo = models.FileField(upload_to='proyectos/documentos/')
    es_publico = models.BooleanField(default=True, verbose_name="¿Es público?")
    requiere_nda = models.BooleanField(default=False, verbose_name="¿Requiere NDA?")
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.titulo}"


# =============================================
# DROPS: Ventanas de Venta por Tiempo Limitado
# =============================================
class ProjectDrop(models.Model):
    """
    Un Drop es una ventana de venta con fecha de inicio/fin y stock limitado.
    Genera urgencia (FOMO) y controla el flujo de caja del proyecto.
    """
    proyecto = models.ForeignKey(
        'Proyecto',
        on_delete=models.CASCADE,
        related_name='drops',
        help_text='Proyecto al que pertenece este Drop.'
    )
    nombre = models.CharField(
        max_length=100,
        help_text='Nombre del drop (ej: "Drop #1 - Early Bird", "Drop #2 - Público")'
    )
    descripcion = models.TextField(
        blank=True,
        help_text='Descripción corta del drop (ej: "Precio especial para los primeros inversores")'
    )

    # Ventana de tiempo
    fecha_inicio = models.DateTimeField(
        help_text='Fecha y hora en que se abre la venta (UTC o timezone del proyecto)'
    )
    fecha_fin = models.DateTimeField(
        help_text='Fecha y hora en que se cierra la venta'
    )

    # Stock por drop
    tokens_disponibles_drop = models.PositiveIntegerField(
        default=100,
        help_text='Cantidad de tokens disponibles SOLO en este drop'
    )
    tokens_vendidos_drop = models.PositiveIntegerField(
        default=0,
        help_text='Tokens vendidos durante este drop (se actualiza automáticamente)'
    )

    # Precio override (opcional - permite precio especial por drop)
    precio_override = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Precio especial para este drop (deja vacío para usar el precio del proyecto)'
    )

    # Límite anti-ballena (máximo tokens por usuario en este drop)
    max_tokens_por_usuario = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text='Máx. tokens que un solo usuario puede comprar en este Drop. Vacío = sin límite.'
    )

    activo = models.BooleanField(
        default=True,
        help_text='Si está desactivado, el drop no se muestra aunque esté en rango de fechas.'
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['fecha_inicio']
        verbose_name = 'Drop (Ventana de Venta)'
        verbose_name_plural = 'Drops (Ventanas de Venta)'

    def __str__(self):
        return f"{self.proyecto.nombre} - {self.nombre}"

    @property
    def esta_en_vivo(self):
        """¿El drop está activo AHORA?"""
        now = timezone.now()
        return self.activo and self.fecha_inicio <= now <= self.fecha_fin

    @property
    def esta_proximo(self):
        """¿El drop aún no ha empezado?"""
        now = timezone.now()
        return self.activo and now < self.fecha_inicio

    @property
    def ya_termino(self):
        """¿El drop ya finalizó?"""
        now = timezone.now()
        return now > self.fecha_fin

    @property
    def tokens_restantes(self):
        """Tokens que quedan disponibles en este drop."""
        return max(0, self.tokens_disponibles_drop - self.tokens_vendidos_drop)

    @property
    def porcentaje_vendido_drop(self):
        """% de tokens vendidos en este drop."""
        if self.tokens_disponibles_drop > 0:
            return round((self.tokens_vendidos_drop / self.tokens_disponibles_drop) * 100, 1)
        return 0

    @property
    def precio_efectivo(self):
        """Precio a aplicar: override del drop o precio del proyecto."""
        return self.precio_override if self.precio_override else self.proyecto.precio_token

    @property
    def estado_display(self):
        """Estado legible del drop."""
        if not self.activo:
            return 'Desactivado'
        if self.esta_en_vivo:
            if self.tokens_restantes <= 0:
                return 'Agotado'
            return 'EN VIVO'
        if self.esta_proximo:
            return 'Próximamente'
        return 'Finalizado'

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

    # === KYC ESCALONADO (TIERS) ===
    TIER_0_BASIC = 0
    TIER_1_VERIFIED = 1
    TIER_2_WHALE = 2
    
    TIER_CHOICES = [
        (TIER_0_BASIC, 'Nivel 0 (Básico - $500)'),
        (TIER_1_VERIFIED, 'Nivel 1 (Verificado - $10k)'),
        (TIER_2_WHALE, 'Nivel 2 (Whale - Ilimitado)'),
    ]
    kyc_tier = models.PositiveSmallIntegerField(default=TIER_0_BASIC, choices=TIER_CHOICES, help_text="Nivel de verificación actual")
    investment_total_usd = models.DecimalField(max_digits=12, decimal_places=2, default=0, help_text="Total invertido acumulado (USD)")

    @property
    def limit_usd(self):
        if self.kyc_tier == 0: return 500
        if self.kyc_tier == 1: return 10000
        return 999999999

    @property
    def calculated_investment_total(self):
        """Calcula el total invertido sumando las reservas confirmadas."""
        from django.db.models import Sum
        # Filtra por estado 'CONFIRMADO' (ver Reserva.ESTADO_CONFIRMADO)
        total = self.user.reserva_set.filter(estado_pago='CONFIRMADO').aggregate(Sum('total'))['total__sum']
        return total or 0

    @property
    def remaining_limit(self):
        # Usa el valor calculado en tiempo real
        return max(0, float(self.limit_usd) - float(self.calculated_investment_total))

    
    # KYC Documents
    documento_identidad_frontal = models.ImageField(upload_to='kyc/documentos/', blank=True, null=True)
    documento_identidad_reverso = models.ImageField(upload_to='kyc/documentos/', blank=True, null=True)
    selfie_verificacion = models.ImageField(upload_to='kyc/selfies/', blank=True, null=True)
    
    fecha_kyc = models.DateTimeField(null=True, blank=True)
    comentarios_admin = models.TextField(blank=True, null=True)
    
    # Métodos de Certificación / Firma
    METODO_FIRMA_VIRTUAL = 'FIRMA_VIRTUAL'
    METODO_SMART_CONTRACT = 'SMART_CONTRACT'
    
    METODO_CHOICES = [
        (METODO_FIRMA_VIRTUAL, 'Contrato Legal (FirmaVirtual)'),
        (METODO_SMART_CONTRACT, 'Título Digital (Smart Contract) - Próximamente'),
    ]
    
    metodo_certificacion = models.CharField(
        max_length=20,
        choices=METODO_CHOICES,
        default=METODO_FIRMA_VIRTUAL,
        help_text="Elija cómo desea certificar su propiedad"
    )
    wallet_address = models.CharField(max_length=100, blank=True, null=True, help_text="Dirección de billetera (Opcional)")

    # =============================================
    # ROL FRACCIONADOR (KYB - Know Your Business)
    # =============================================
    USER_TYPE_CHOICES = [
        ('INVESTOR', 'Inversionista'),
        ('FRACTIONALIZER', 'Fraccionador (Vendedor)'),
    ]
    user_type = models.CharField(
        max_length=20,
        choices=USER_TYPE_CHOICES,
        default='INVESTOR',
        help_text="Rol del usuario en la plataforma."
    )

    KYB_STATUS_CHOICES = [
        ('NONE', 'No Iniciado'),
        ('REVIEW', 'En Revisión'),
        ('APPROVED', 'Aprobado'),
        ('REJECTED', 'Rechazado'),
    ]
    kyb_status = models.CharField(
        max_length=15,
        choices=KYB_STATUS_CHOICES,
        default='NONE',
        help_text="Estado de verificación de empresa (solo para Fraccionadores)."
    )

    # Datos empresa
    company_name = models.CharField(max_length=200, blank=True, null=True, verbose_name="Razón Social")
    company_tax_id = models.CharField(max_length=20, blank=True, null=True, verbose_name="RUT Empresa")
    company_legal_rep = models.CharField(max_length=100, blank=True, null=True, verbose_name="Representante Legal")
    
    # Documentos KYB
    company_docs = models.FileField(
        upload_to='kyb/docs/', 
        blank=True, 
        null=True, 
        help_text="Escritura o Constitución de la empresa (PDF)"
    )

    def __str__(self):
        return f"Perfil de {self.user.username}"

    class Meta:
        verbose_name = "Perfil de Usuario"
        verbose_name_plural = "Perfiles de Usuario"

# --- PERFIL DE USUARIO PARA KYC (NUEVO) ---

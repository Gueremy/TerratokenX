from django.contrib import admin
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from import_export.admin import ImportExportModelAdmin
from .models import Reserva, DiaFeriado, Coupon, Configuracion, Proyecto, UserProfile, ProjectDrop

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'kyc_status', 'fecha_kyc')
    list_filter = ('kyc_status',)
    search_fields = ('user__username', 'user__email', 'rut')

class ProjectDropInline(admin.TabularInline):
    model = ProjectDrop
    extra = 0
    fields = ('nombre', 'fecha_inicio', 'fecha_fin', 'tokens_disponibles_drop', 'tokens_vendidos_drop', 'precio_override', 'activo')
    readonly_fields = ('tokens_vendidos_drop',)


@admin.register(Proyecto)
class ProyectoAdmin(ImportExportModelAdmin):
    list_display = ('nombre', 'owner_type', 'compliance_status', 'docs_status', 'precio_token', 'tokens_vendidos', 'activo')
    list_filter = ('owner_type', 'compliance_status', 'docs_status', 'tipo', 'estado', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    list_editable = ('activo', 'precio_token', 'compliance_status', 'docs_status')
    search_fields = ('nombre', 'slug', 'spv_legal_name')
    inlines = [ProjectDropInline]

    fieldsets = (
        ('Información General', {
            'fields': ('nombre', 'slug', 'descripcion', 'ubicacion', 'tipo', 'estado',
                       'imagen_portada', 'imagen_portada_url', 'video_url', 'pagina_oficial_url')
        }),
        ('Marketplace (Interno vs Externo)', {
            'fields': ('owner_type', 'owner'),
            'description': 'Define si este proyecto es Premium (Joan) o del Marketplace (Fraccionador externo).',
        }),
        ('Compliance & Documentación', {
            'fields': ('compliance_status', 'docs_status', 'archivo_propiedad'),
        }),
        ('Metadatos RWA (Pre-Blockchain)', {
            'fields': ('gps_data', 'spv_legal_name', 'legal_hash', 'docs_manifest_hash', 'data_room_url'),
            'classes': ('collapse',),
            'description': 'Datos que se usarán para tokenización futura (ERC-3643).',
        }),
        ('Tokenomics & Financiamiento', {
            'fields': ('precio_token', 'tokens_totales', 'rentabilidad_estimada',
                       'activo', 'financiamiento_activo'),
        }),
    )


@admin.register(ProjectDrop)
class ProjectDropAdmin(admin.ModelAdmin):
    list_display = ('nombre', 'proyecto', 'fecha_inicio', 'fecha_fin', 'tokens_disponibles_drop', 'tokens_vendidos_drop', 'estado_badge', 'activo')
    list_filter = ('proyecto', 'activo')
    search_fields = ('nombre', 'proyecto__nombre')
    ordering = ('-fecha_inicio',)
    readonly_fields = ('tokens_vendidos_drop', 'created_at')

    @admin.display(description='Estado')
    def estado_badge(self, obj):
        estado = obj.estado_display
        colors = {
            'EN VIVO': 'green',
            'Próximamente': 'orange',
            'Finalizado': 'gray',
            'Agotado': 'red',
            'Desactivado': 'gray',
        }
        color = colors.get(estado, 'gray')
        return format_html('<span style="color: {};font-weight:bold">{}</span>', color, estado)

@admin.register(Reserva)
class ReservaAdmin(ImportExportModelAdmin):
    """
    Configuración avanzada para el modelo Reserva en el panel de administración.
    """
    list_display = (
        'numero_reserva',
        'proyecto_link', # Mostrar proyecto
        'nombre',
        'cantidad_tokens',
        'total_formatted',
        'estado_pago',
        'created_at'
    )
    list_filter = ('proyecto', 'estado_pago', 'created_at') # Filtro por proyecto añadido
    search_fields = ('nombre', 'numero_reserva')
    date_hierarchy = 'created_at'
    ordering = ('-created_at',)

    @admin.display(description='Proyecto', ordering='proyecto')
    def proyecto_link(self, obj):
        return obj.proyecto.nombre if obj.proyecto else "N/A"

    @admin.display(description='Total', ordering='total')
    def total_formatted(self, obj):
        """Formatea el total como moneda chilena."""
        return f"${intcomma(int(obj.total))}"

# Personalización global del sitio de administración
admin.site.site_header = "Panel de Ventas TerraTokenX"
admin.site.site_title = "Admin TerraTokenX"
admin.site.index_title = "Gestión de Inversiones"

@admin.register(DiaFeriado)
class DiaFeriadoAdmin(admin.ModelAdmin):
    list_display = ('fecha', 'descripcion')
    ordering = ('fecha',)

@admin.register(Coupon)
class CouponAdmin(admin.ModelAdmin):
    list_display = ('code', 'discount_percentage', 'is_active', 'valid_from', 'valid_to')
    list_filter = ('is_active',)
    search_fields = ('code',)

@admin.register(Configuracion)
class ConfiguracionAdmin(admin.ModelAdmin):
    """
    Admin para el modelo singleton de Configuración.
    Permite editar los precios pero no crear nuevas configuraciones ni eliminar la existente.
    """
    list_display = ('__str__', 'precio_base_token_formatted')

    @admin.display(description='Precio Base Token')
    def precio_base_token_formatted(self, obj):
        """Formatea el precio como moneda chilena."""
        return f"${intcomma(obj.precio_base_token)}"

    def has_add_permission(self, request):
        # Prevenir que se creen nuevas instancias si ya existe una.
        return not Configuracion.objects.exists()

    def has_delete_permission(self, request, obj=None):
        # Prevenir que se elimine la configuración.
        return False

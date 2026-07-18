from django.contrib import admin
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from import_export.admin import ImportExportModelAdmin
from .models import (
    AuditLog,
    Configuracion,
    Coupon,
    CreditBalance,
    CreditTransaction,
    DiaFeriado,
    FeeConfig,
    FraccionadorProfile,
    ProjectDrop,
    Proyecto,
    Reserva,
    TierConfig,
    UserProfile,
)

@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'rut', 'kyc_status', 'kyc_tier', 'investment_total_usd', 'fecha_kyc')
    list_filter = ('kyc_status', 'kyc_tier')
    search_fields = ('user__username', 'user__email', 'rut')

@admin.register(Proyecto)
class ProyectoAdmin(ImportExportModelAdmin):
    list_display = ('nombre', 'precio_token', 'tokens_vendidos', 'activo')
    prepopulated_fields = {'slug': ('nombre',)}
    list_editable = ('activo', 'precio_token')

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


# ── Drops, Créditos y Fees ──────────────────────────────────────────────────

@admin.register(ProjectDrop)
class ProjectDropAdmin(admin.ModelAdmin):
    list_display = ('proyecto', 'nombre', 'numero', 'stock_disponible', 'stock_total',
                    'precio_override', 'fecha_inicio', 'fecha_fin', 'activo')
    list_filter = ('activo', 'proyecto')
    list_editable = ('activo',)
    ordering = ('proyecto', 'numero')


@admin.register(TierConfig)
class TierConfigAdmin(admin.ModelAdmin):
    list_display = ('tier', 'nombre', 'cap_creditos_usd', 'descuento_fees_pct',
                    'descuento_creditos_pct', 'kyc_requerido')
    ordering = ('tier',)


@admin.register(FeeConfig)
class FeeConfigAdmin(admin.ModelAdmin):
    list_display = ('tipo', 'porcentaje', 'monto_minimo_usd', 'activo', 'descripcion')
    list_editable = ('porcentaje', 'monto_minimo_usd', 'activo')


@admin.register(CreditBalance)
class CreditBalanceAdmin(admin.ModelAdmin):
    list_display = ('user', 'balance_usd', 'tier', 'expires_at', 'extended')
    list_filter = ('tier', 'extended')
    search_fields = ('user__username', 'user__email')


@admin.register(CreditTransaction)
class CreditTransactionAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo', 'monto_usd', 'reserva', 'descripcion', 'created_at')
    list_filter = ('tipo',)
    search_fields = ('user__username', 'user__email', 'descripcion')
    date_hierarchy = 'created_at'

    def has_change_permission(self, request, obj=None):
        return False  # registro inmutable

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(AuditLog)
class AuditLogAdmin(admin.ModelAdmin):
    list_display = ('accion', 'objeto_tipo', 'objeto_id', 'user', 'ip_address', 'created_at')
    list_filter = ('accion', 'objeto_tipo')
    search_fields = ('accion', 'objeto_tipo')
    date_hierarchy = 'created_at'

    def has_add_permission(self, request):
        return False  # inmutable: solo lectura

    def has_change_permission(self, request, obj=None):
        return False

    def has_delete_permission(self, request, obj=None):
        return False


@admin.register(FraccionadorProfile)
class FraccionadorProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'tipo', 'kyb_estado', 'razon_social', 'kyb_fecha_aprobacion')
    list_filter = ('kyb_estado', 'tipo')
    search_fields = ('user__username', 'user__email', 'razon_social', 'rut_empresa')

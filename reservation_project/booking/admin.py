from django.contrib import admin
from django.utils.html import format_html
from django.contrib.humanize.templatetags.humanize import intcomma
from import_export.admin import ImportExportModelAdmin
from .models import Reserva, DiaFeriado, Coupon, Configuracion, Proyecto

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

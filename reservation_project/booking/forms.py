from django import forms
from django.forms import inlineformset_factory
from .models import Reserva, DiaFeriado, Coupon, Proyecto, ProyectoImagen
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from dns import resolver

# Formulario para imágenes de galería
class ProyectoImagenForm(forms.ModelForm):
    class Meta:
        model = ProyectoImagen
        fields = ['imagen', 'imagen_url', 'caption']
        widgets = {
            'imagen': forms.FileInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'imagen_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'https://ejemplo.com/imagen.jpg'}),
            'caption': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
        }

# Inline formset para la galería de imágenes del proyecto
ProyectoImagenFormSet = inlineformset_factory(Proyecto, ProyectoImagen, form=ProyectoImagenForm, extra=2, max_num=10, can_delete=True)


class ReservaForm(forms.ModelForm):
    coupon_code = forms.CharField(max_length=50, required=False, label="Código de Cupón", help_text="Opcional")
    class Meta:
        model = Reserva
        fields = ['nombre', 'correo', 'telefono', 'rut', 'direccion', 'cantidad_tokens', 'proyecto', 'es_empresa', 'razon_social', 'rut_empresa', 'cargo_representante']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Nombre completo'}),
            'correo': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'correo@ejemplo.com'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': '+56912345678'}),
            'rut': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': '12345678-9'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'cantidad_tokens': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'min': '1', 'value': '1'}),
            'proyecto': forms.HiddenInput(),
            
            # Persona Jurídica
            'es_empresa': forms.CheckboxInput(attrs={'class': 'w-4 h-4 text-blue-600 bg-gray-100 border-gray-300 rounded focus:ring-blue-500', 'id': 'check_es_empresa'}),
            'razon_social': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Razón Social S.A.'}),
            'rut_empresa': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': '76.123.456-7'}),
            'cargo_representante': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'placeholder': 'Gerente General'}),
        }
        labels = {
            'rut': 'RUT (obligatorio para contrato)',
            'telefono': 'Teléfono (para recibir el contrato)',
        }
    
    def clean_rut(self):
        rut = self.cleaned_data.get('rut')
        if not rut:
            raise ValidationError("El RUT es obligatorio para generar el contrato legal.")
        # Limpiar puntos si los puso
        rut = rut.replace(".", "")
        return rut
    
    def clean_telefono(self):
        telefono = self.cleaned_data.get('telefono')
        if not telefono:
            raise ValidationError("El teléfono es obligatorio para recibir el contrato.")
        return telefono
    
    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            try:
                coupon = Coupon.objects.get(code__iexact=code)  # Case-insensitive match
                if not coupon.is_valid():
                    raise ValidationError("El cupón no es válido o ha expirado.")
                return coupon  # Return the coupon object, not just the code
            except Coupon.DoesNotExist:
                raise ValidationError("El código de cupón no existe.")
        return None  # Return None if no code was entered

class AdminReservaForm(forms.ModelForm):
    coupon_code = forms.CharField(max_length=50, required=False, label="Código de Cupón", help_text="Opcional")
    
    class Meta:
        model = Reserva
        fields = ['nombre', 'correo', 'telefono', 'direccion', 'cantidad_tokens', 'proyecto', 'estado_pago']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
            'correo': forms.EmailInput(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
            'cantidad_tokens': forms.NumberInput(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white', 'min': '1'}),
            'proyecto': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
            'estado_pago': forms.Select(attrs={'class': 'w-full px-4 py-3 bg-dark-700 border border-gray-600 rounded-lg text-white'}),
        }
    
    def clean_coupon_code(self):
        code = self.cleaned_data.get('coupon_code')
        if code:
            try:
                coupon = Coupon.objects.get(code=code)
                if not coupon.is_valid():
                    raise ValidationError("El cupón no es válido o ha expirado.")
                return coupon # Return the coupon object, not just the code
            except Coupon.DoesNotExist:
                raise ValidationError("El código de cupón no existe.")
        return None # Return None if no code was entered

class ProyectoForm(forms.ModelForm):
    class Meta:
        from .models import Proyecto
        model = Proyecto
        fields = [
            'nombre', 'slug', 'descripcion', 'ubicacion', 
            'owner_type', 'owner', 'compliance_status', 'docs_status',
            'spv_legal_name', 'legal_hash', 'data_room_url', 'gps_data',
            'precio_token', 'tokens_totales', 'rentabilidad_estimada', 
            'imagen_portada', 'imagen_portada_url', 'video_url', 
            'activo', 'financiamiento_activo', 'venta_solo_drops',
            'tipo', 'estado', 'pagina_oficial_url'
        ]
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'slug': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'rows': 4}),
            'ubicacion': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            
            # Marketplace & Compliance
            'owner_type': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'owner': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'compliance_status': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'docs_status': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            
            # RWA Metadatos
            'spv_legal_name': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'Ej: Refugio Patagonia SpA'}),
            'legal_hash': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white font-mono text-xs'}),
            'data_room_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'gps_data': forms.Textarea(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white font-mono text-xs', 'rows': 3, 'placeholder': '{"lat": -41.0, "lng": -72.0}'}),

            'precio_token': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'tokens_totales': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'rentabilidad_estimada': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'imagen_portada': forms.FileInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'imagen_portada_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'https://ejemplo.com/imagen.jpg'}),
            'video_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'w-5 h-5 bg-gray-700 border-gray-600 rounded'}),
            'tipo': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'estado': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'pagina_oficial_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
        }


class ProjectDropForm(forms.ModelForm):
    porcentaje_tokens = forms.IntegerField(
        min_value=1,
        max_value=100,
        label='Porcentaje de Tokens (%)',
        help_text='Porcentaje de los tokens TOTALES del proyecto para este Drop.',
        widget=forms.NumberInput(attrs={
            'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white',
            'placeholder': 'Ej: 20 (para 20%)',
            'min': '1',
            'max': '100',
        })
    )

    class Meta:
        from .models import ProjectDrop
        model = ProjectDrop
        fields = ['nombre', 'descripcion', 'fecha_inicio', 'fecha_fin', 'precio_override', 'max_tokens_por_usuario', 'activo']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'Ej: Drop #1 - Early Bird'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'rows': 3}),
            'fecha_inicio': forms.DateTimeInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'type': 'datetime-local'}),
            'fecha_fin': forms.DateTimeInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'type': 'datetime-local'}),
            'precio_override': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'Opcional: Precio especial para este Drop'}),
            'max_tokens_por_usuario': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'Opcional: Ej. 5 (vacío = sin límite)'}),
            'activo': forms.CheckboxInput(attrs={'class': 'w-5 h-5 bg-gray-700 border-gray-600 rounded'}),
        }
        labels = {
            'precio_override': 'Precio Especial (USD)',
            'max_tokens_por_usuario': 'Máx. Tokens por Persona 🐋',
        }

    def __init__(self, *args, proyecto=None, **kwargs):
        super().__init__(*args, **kwargs)
        self.proyecto = proyecto
        # Si estamos editando, pre-calcular el porcentaje desde tokens existentes
        if self.instance and self.instance.pk and self.proyecto:
            pct = round((self.instance.tokens_disponibles_drop / self.proyecto.tokens_totales) * 100) if self.proyecto.tokens_totales > 0 else 0
            self.fields['porcentaje_tokens'].initial = pct

    def clean_porcentaje_tokens(self):
        porcentaje = self.cleaned_data.get('porcentaje_tokens')
        if not self.proyecto:
            return porcentaje

        tokens_totales = self.proyecto.tokens_totales
        if tokens_totales <= 0:
            raise forms.ValidationError("El proyecto no tiene tokens configurados.")

        # Calcular tokens ya asignados a OTROS drops
        from .models import ProjectDrop
        otros_drops = ProjectDrop.objects.filter(proyecto=self.proyecto)
        if self.instance and self.instance.pk:
            otros_drops = otros_drops.exclude(pk=self.instance.pk)

        tokens_en_otros_drops = sum(d.tokens_disponibles_drop for d in otros_drops)
        tokens_libres = tokens_totales - tokens_en_otros_drops
        porcentaje_libre = round((tokens_libres / tokens_totales) * 100, 1) if tokens_totales > 0 else 0

        tokens_solicitados = round(tokens_totales * porcentaje / 100)

        if tokens_solicitados > tokens_libres:
            raise forms.ValidationError(
                f"Excedes los tokens disponibles. Quedan {tokens_libres} tokens libres "
                f"({porcentaje_libre}% restante). Pide máximo {porcentaje_libre}%."
            )

        return porcentaje


# FORMULARIO ESPECFICO PARA FRACCIONADORES (Solo campos editables)
class FractionalizerProjectForm(forms.ModelForm):
    class Meta:
        from .models import Proyecto
        model = Proyecto
        fields = [
            'nombre', 'descripcion', 'ubicacion', 
            'spv_legal_name', 'data_room_url', # RWA Partial
            'precio_token', 'tokens_totales', 'rentabilidad_estimada',
            'imagen_portada', 'imagen_portada_url', 'video_url',
            'financiamiento_activo', 'venta_solo_drops',
            'tipo', 'pagina_oficial_url'
        ]
        # Exclumos slug, owner_type, compliance_status, docs_status, estado, gps_data (manual), legal_hash (readonly)
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'descripcion': forms.Textarea(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full', 'rows': 4}),
            'ubicacion': forms.TextInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'spv_legal_name': forms.TextInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'data_room_url': forms.URLInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'precio_token': forms.NumberInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'tokens_totales': forms.NumberInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'rentabilidad_estimada': forms.TextInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'imagen_portada': forms.FileInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'imagen_portada_url': forms.URLInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'video_url': forms.URLInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'financiamiento_activo': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-gray-700 bg-dark-900 text-emerald-500'}),
            'venta_solo_drops': forms.CheckboxInput(attrs={'class': 'w-5 h-5 rounded border-gray-700 bg-dark-900 text-red-500'}),
            'tipo': forms.Select(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
            'pagina_oficial_url': forms.URLInput(attrs={'class': 'bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full'}),
        }

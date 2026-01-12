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
        fields = ['nombre', 'correo', 'telefono', 'direccion', 'cantidad_tokens', 'proyecto']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'correo': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'cantidad_tokens': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'min': '1', 'value': '1'}),
            'proyecto': forms.HiddenInput(),
        }
    
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
        fields = ['nombre', 'slug', 'descripcion', 'ubicacion', 'precio_token', 'tokens_totales', 'rentabilidad_estimada', 'imagen_portada', 'imagen_portada_url', 'video_url', 'activo', 'tipo', 'estado', 'pagina_oficial_url']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'slug': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'descripcion': forms.Textarea(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'rows': 4}),
            'ubicacion': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'precio_token': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'tokens_totales': forms.NumberInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'rentabilidad_estimada': forms.TextInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'imagen_portada': forms.FileInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'imagen_portada_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'https://ejemplo.com/imagen.jpg'}),
            'video_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white', 'placeholder': 'https://www.youtube.com/watch?v=...'}),
            'activo': forms.CheckboxInput(attrs={'class': 'w-5 h-5'}),
            'tipo': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'estado': forms.Select(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
            'pagina_oficial_url': forms.URLInput(attrs={'class': 'w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white'}),
        }

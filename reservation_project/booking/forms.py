from django import forms
from .models import Reserva, DiaFeriado, Coupon
from datetime import date, datetime, timedelta
from django.core.exceptions import ValidationError
from dns import resolver

class ReservaForm(forms.ModelForm):
    coupon_code = forms.CharField(max_length=50, required=False, label="Código de Cupón", help_text="Opcional")
    class Meta:
        model = Reserva
        fields = ['nombre', 'correo', 'telefono', 'direccion', 'cantidad_tokens']
        widgets = {
            'nombre': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'correo': forms.EmailInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'telefono': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'direccion': forms.TextInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md'}),
            'cantidad_tokens': forms.NumberInput(attrs={'class': 'w-full px-3 py-2 border border-gray-300 rounded-md', 'min': '1', 'value': '1'}),
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

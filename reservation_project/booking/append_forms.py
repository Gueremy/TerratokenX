
# FORMULARIO ESPECÍFICO PARA FRACCIONADORES (Solo campos editables)
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
        # Excluímos slug, owner_type, compliance_status, docs_status, estado, gps_data (manual), legal_hash (readonly)
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

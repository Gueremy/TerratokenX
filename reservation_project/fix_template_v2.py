import re

filepath = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Espacios alrededor de == en tags de Django (por si acaso no se aplicó)
content = content.replace("estado_pago=='PENDIENTE'", "estado_pago == 'PENDIENTE'")
content = content.replace("estado_pago=='EN_REVISION'", "estado_pago == 'EN_REVISION'")
content = content.replace("estado_pago=='CONFIRMADO'", "estado_pago == 'CONFIRMADO'")

# Fix 2: Eliminar completamente el span problemático y reemplazarlo con una estructura limpia
# Buscamos el bloque que empieza con <div class="flex justify-between items-start mb-4 pr-8"> y lo reemplazamos
start_marker = '<div class="flex justify-between items-start mb-4 pr-8">'
end_marker = '<div class="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-8 text-sm text-gray-300">'

# Construimos el nuevo bloque HTML limpio
new_block = '''<div class="flex justify-between items-start mb-4 pr-8">
                        <div>
                            <h3 class="text-xl font-bold text-yellow-400">{{ reserva.nombre }}</h3>
                            <span class="text-xs text-gray-500">ID: {{ reserva.numero_reserva }}</span>
                        </div>
                        
                        {% if reserva.estado_pago == 'CONFIRMADO' %}
                            <span class="px-3 py-1 rounded-full text-xs font-bold bg-green-900 text-green-400">Confirmado</span>
                        {% elif reserva.estado_pago == 'EN_REVISION' %}
                            <span class="px-3 py-1 rounded-full text-xs font-bold bg-orange-900 text-orange-400">En Revision</span>
                        {% else %}
                            <span class="px-3 py-1 rounded-full text-xs font-bold bg-yellow-900 text-yellow-500">Pendiente</span>
                        {% endif %}
                    </div>
                    '''

# Encontrar dónde insertar esto es difícil con replace simple si el contenido varía.
# Vamos a usar regex para encontrar el bloque completo
pattern = re.compile(f'{re.escape(start_marker)}.*?{re.escape(end_marker)}', re.DOTALL)
# Verificamos si encontramos el patrón antes de reemplazar
if pattern.search(content):
    content = pattern.sub(f'{new_block}{end_marker}', content)
    print("Bloque de estado de pago actualizado correctamente.")
else:
    print("No se encontró el bloque de estado de pago para reemplazar.")


# Fix 3: Arreglar el bloque de estado de FirmaVirtual (iconos y texto)
# Simplificamos esas clases dinámicas que causan problemas
fv_status_block_start = '<div class="mt-3 p-3 bg-gray-700/50 rounded-lg">'
fv_status_block_end = '<div class="text-xs text-gray-500 mt-1">ID: {{ reserva.firmavirtual_id|truncatechars:20 }}</div>'

new_fv_block = '''<div class="mt-3 p-3 bg-gray-700/50 rounded-lg">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-2">
                                {% if reserva.firmavirtual_status == 'signed' %}
                                    <span class="material-icons text-sm text-green-400">verified</span>
                                    <span class="text-xs text-green-400 font-medium">Contrato Firmado ✓</span>
                                {% elif reserva.firmavirtual_status == 'rejected' %}
                                    <span class="material-icons text-sm text-red-400">cancel</span>
                                    <span class="text-xs text-red-400 font-medium">Rechazado</span>
                                {% else %}
                                    <span class="material-icons text-sm text-blue-400">schedule</span>
                                    <span class="text-xs text-blue-400 font-medium">Pendiente de Firma</span>
                                {% endif %}
                            </div>
                            {% if reserva.contrato_firmado %}
                            <a href="{{ reserva.contrato_firmado.url }}" target="_blank"
                                class="text-xs bg-green-600 hover:bg-green-700 text-white px-3 py-1 rounded flex items-center gap-1">
                                <span class="material-icons text-sm">download</span>
                                Descargar PDF
                            </a>
                            {% endif %}
                        </div>
                        '''
pattern_fv = re.compile(f'{re.escape(fv_status_block_start)}.*?{re.escape(fv_status_block_end)}', re.DOTALL)
if pattern_fv.search(content):
    content = pattern_fv.sub(f'{new_fv_block}{fv_status_block_end}', content)
    print("Bloque FirmaVirtual actualizado correctamente.")
else:
    print("No se encontró el bloque FirmaVirtual para reemplazar.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Script finalizado.")

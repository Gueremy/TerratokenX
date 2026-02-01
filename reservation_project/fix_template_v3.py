import re

filepath = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# El bloque problemático es el select options. Vamos a reemplazar todo el select options.
# Identificamos el inicio y fin del select
start_str = '<select name="estado_pago"'
end_str = '</select>'

# Construimos el nuevo bloque limpio
new_select_block = '<select name="estado_pago" class="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white">\n                            <option value="">Todos</option>\n                            <option value="PENDIENTE" {% if request.GET.estado_pago == "PENDIENTE" %}selected{% endif %}>Pendiente</option>\n                            <option value="EN_REVISION" {% if request.GET.estado_pago == "EN_REVISION" %}selected{% endif %}>En Revision</option>\n                            <option value="CONFIRMADO" {% if request.GET.estado_pago == "CONFIRMADO" %}selected{% endif %}>Confirmado</option>\n                        '

# Usamos regex para reemplazar lo que haya entre <select...> y </select>
import re
pattern = re.compile(f'{re.escape(start_str)}.*?{re.escape(end_str)}', re.DOTALL)

if pattern.search(content):
    content = pattern.sub(f'{new_select_block}{end_str}', content)
    print("Select block fixed.")
else:
    print("Could not find select block.")

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

import re

file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_v6.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# 1. Fix missing spaces around == in generic cases
# Be careful not to match inside string literals if possible, but for this template it's mostly simple variables
content = re.sub(r"request\.GET\.estado_pago=='([^']+)'", r"request.GET.estado_pago == '\1'", content)
content = re.sub(r"request\.GET\.metodo_pago=='([^']+)'", r"request.GET.metodo_pago == '\1'", content)
content = re.sub(r"reserva\.estado_pago=='([^']+)'", r"reserva.estado_pago == '\1'", content)
content = re.sub(r"reserva\.metodo_pago=='([^']+)'", r"reserva.metodo_pago == '\1'", content)

# 2. Fix broken multiline tags for the filter options (consolidate to single line)
# Matches: <option ... {% if ... %}selected{% \n endif %}>...
content = re.sub(
    r'(<option value="[^"]+" \{% if [^%]+ \%\})\s*selected\{\%\s*\n\s*endif\s*\%\}',
    r'\1selected{% endif %}',
    content
)

# 3. Fix the specific status badge block (lines 79-81 approx)
# We'll just replace the known broken block pattern with a clean one
broken_badge_pattern = r'class="px-3 py-1 rounded-full text-xs font-bold \{% if reserva\.estado_pago == \'CONFIRMADO\' %\}bg-green-900 text-green-400\{% elif reserva\.estado_pago == \'EN_REVISION\' %\}bg-orange-900 text-orange-400\{% else %\}bg-yellow-900 text-yellow-500\{% endif %\}">\{\%\s*if reserva\.estado_pago == \'CONFIRMADO\' %\}Confirmado\{\% elif reserva\.estado_pago ==\s*\'EN_REVISION\' %\}En Revision\{\% else %\}Pendiente\{\% endif %\}</span>'
clean_badge = r'class="px-3 py-1 rounded-full text-xs font-bold {% if reserva.estado_pago == \'CONFIRMADO\' %}bg-green-900 text-green-400{% elif reserva.estado_pago == \'EN_REVISION\' %}bg-orange-900 text-orange-400{% else %}bg-yellow-900 text-yellow-500{% endif %}">{% if reserva.estado_pago == \'CONFIRMADO\' %}Confirmado{% elif reserva.estado_pago == \'EN_REVISION\' %}En Revision{% else %}Pendiente{% endif %}</span>'

# Try to match the multiline version if regex allows, otherwise we might rely on the previous "spaces fix" having partially fixed it
# Let's try a more aggressive replacement for the whole file content for the specific complex lines

# Fix filter section manually if regex fails
if "request.GET.estado_pago=='PENDIENTE'" in content:
    content = content.replace("request.GET.estado_pago=='PENDIENTE'", "request.GET.estado_pago == 'PENDIENTE'")
if "request.GET.estado_pago=='EN_REVISION'" in content:
    content = content.replace("request.GET.estado_pago=='EN_REVISION'", "request.GET.estado_pago == 'EN_REVISION'")
if "request.GET.estado_pago=='CONFIRMADO'" in content:
    content = content.replace("request.GET.estado_pago=='CONFIRMADO'", "request.GET.estado_pago == 'CONFIRMADO'")

# Fix broken endif newlines globally again just in case
content = re.sub(r'selected\{%\s*\n\s*endif\s*%\}', 'selected{% endif %}', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed v6 template!")

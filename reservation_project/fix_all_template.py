import pathlib
import re
import time

file_path = pathlib.Path('booking/templates/booking/admin_panel_v3.html')

time.sleep(0.5)
content = file_path.read_text(encoding='utf-8')
original = content

# Fix 1: Split endif in messages block
content = re.sub(
    r'check_circle\{%\s*\r?\n\s*endif\s*%\}',
    'check_circle{% endif %}',
    content
)

# Fix 2: Split ID display {{ reserva.numero_reserva...
content = re.sub(
    r'ID: \{\{\s*\r?\n\s*reserva\.numero_reserva\|default:"N/A"\s*\}\}',
    'ID: {{ reserva.numero_reserva|default:"N/A" }}',
    content
)

# Fix 3: Split date {{ reserva.created_at|date:"d...
content = re.sub(
    r'\{\{ reserva\.created_at\|date:"d\s*\r?\n\s*M Y H:i"\s*\}\}',
    '{{ reserva.created_at|date:"d M Y H:i" }}',
    content
)

# Fix 4: Split if for estado_pago display in badge text
content = re.sub(
    r'\{% if reserva\.estado_pago ==\s*\r?\n\s*\'EN_REVISION\' %\}',
    "{% if reserva.estado_pago == 'EN_REVISION' %}",
    content
)

# Fix 5: Split if for payment method
content = re.sub(
    r'>\{%\s*\r?\n\s*if reserva\.metodo_pago == \'MP\' %\}credit_card',
    '>{% if reserva.metodo_pago == \'MP\' %}credit_card',
    content
)

file_path.write_text(content, encoding='utf-8')

if content != original:
    print("Changes applied!")
else:
    print("No changes needed")

# Verify key fixes
new_content = file_path.read_text(encoding='utf-8')
if 'check_circle{% endif %}' in new_content:
    print("✓ Split endif fixed")
if '{{ reserva.numero_reserva|default:"N/A" }}' in new_content:
    print("✓ Reservation ID fixed")
if '{{ reserva.created_at|date:"d M Y H:i" }}' in new_content:
    print("✓ Date format fixed")

import pathlib
import time

file_path = pathlib.Path('booking/templates/booking/admin_panel_v3.html')
content = file_path.read_text(encoding='utf-8')

# Fix 1: Filter dropdown options (lines 67-72)
old_filter = """                            <option value="PENDIENTE" {% if request.GET.estado_pago=='PENDIENTE' %}selected{% endif %}>
                                Pendiente</option>
                            <option value="EN_REVISION" {% if request.GET.estado_pago=='EN_REVISION' %}selected{% endif
                                %}>En Revisión</option>
                            <option value="CONFIRMADO" {% if request.GET.estado_pago=='CONFIRMADO' %}selected{% endif
                                %}>Confirmado</option>"""

new_filter = """                            <option value="PENDIENTE" {% if request.GET.estado_pago == 'PENDIENTE' %}selected{% endif %}>Pendiente</option>
                            <option value="EN_REVISION" {% if request.GET.estado_pago == 'EN_REVISION' %}selected{% endif %}>En Revisión</option>
                            <option value="CONFIRMADO" {% if request.GET.estado_pago == 'CONFIRMADO' %}selected{% endif %}>Confirmado</option>"""

content = content.replace(old_filter, new_filter)

# Fix 2: Split badge text (lines 109-110)
old_badge = """{% if reserva.estado_pago == 'CONFIRMADO' %}Confirmado{% elif reserva.estado_pago ==
                            'EN_REVISION' %}En Revisión{% else %}Pendiente{% endif %}"""

new_badge = """{% if reserva.estado_pago == 'CONFIRMADO' %}Confirmado{% elif reserva.estado_pago == 'EN_REVISION' %}En Revisión{% else %}Pendiente{% endif %}"""

content = content.replace(old_badge, new_badge)

# Write and sync
file_path.write_text(content, encoding='utf-8')

# Force flush
import os
os.sync() if hasattr(os, 'sync') else None

time.sleep(0.5)

# Verify
verify = file_path.read_text(encoding='utf-8')
if "estado_pago == 'PENDIENTE'" in verify:
    print("✓ Filter options fixed!")
else:
    print("✗ Filter options NOT fixed")
    
if "estado_pago == 'EN_REVISION' %}En Revisión" in verify:
    print("✓ Badge text fixed!")
else:
    print("✗ Badge text NOT fixed")

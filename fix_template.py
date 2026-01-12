import re

path = 'reservation_project/booking/templates/booking/admin_panel_v3.html'
with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# Fix comparison operators  
c = c.replace("=='PENDIENTE'", " == 'PENDIENTE'")
c = c.replace("=='EN_REVISION'", " == 'EN_REVISION'")
c = c.replace("=='CONFIRMADO'", " == 'CONFIRMADO'")

# Fix split {% if tags
c = re.sub(r'\{%\s*\r?\n\s*if\s+', '{% if ', c)

# Fix split estado_pago == 'EN_REVISION'
c = re.sub(r'reserva\.estado_pago\s*==\s*\r?\n\s*\'EN_REVISION\'', "reserva.estado_pago == 'EN_REVISION'", c)

# Fix split endif tags  
c = re.sub(r'\{%\s*endif\s*\r?\n\s*%\}', '{% endif %}', c)
c = re.sub(r'selected\s*\{%\s*endif\s*\r?\n\s*%\}', 'selected{% endif %}', c)

with open(path, 'w', encoding='utf-8') as f:
    f.write(c)
    
print('Fixed!')

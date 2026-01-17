import re

filepath = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Buscamos el bloque del cupón que tiene formato raro
# El screenshot muestra: Cupon: {{ reserva.coupon.code }} (-30%)
# Lo vamos a reemplazar por una versión limpia en una sola línea

# Buscar versiones quebradas por saltos de línea
old_coupon_block = r'{% if reserva.coupon %}.*?{% endif %}'

# Nuevo bloque limpio
new_coupon_block = '{% if reserva.coupon %}<div class="mt-2"><span class="bg-green-900 text-green-400 px-2.5 py-0.5 rounded-full text-xs">Cupon: {{ reserva.coupon.code }} (-{{ reserva.coupon.discount_percentage }}%)</span></div>{% endif %}'

# Usamos regex con DOTALL para que el punto coincida con newlines
content = re.sub(r'{%\s*if\s+reserva\.coupon\s*%}.*?{%\s*endif\s*%}', new_coupon_block, content, flags=re.DOTALL)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("Coupon display fixed.")

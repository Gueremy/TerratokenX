import re

filepath = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

with open(filepath, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix 1: Espacios alrededor de == en tags de Django
content = content.replace("estado_pago=='PENDIENTE'", "estado_pago == 'PENDIENTE'")
content = content.replace("estado_pago=='EN_REVISION'", "estado_pago == 'EN_REVISION'")
content = content.replace("estado_pago=='CONFIRMADO'", "estado_pago == 'CONFIRMADO'")

# Fix 2: Arreglar el span con el if roto (lineas 110-113)
old_span = '''<span
                            class="px-3 py-1 rounded-full text-xs font-bold {% if reserva.estado_pago == 'CONFIRMADO' %}bg-green-900 text-green-400{% elif reserva.estado_pago == 'EN_REVISION' %}bg-orange-900 text-orange-400{% else %}bg-yellow-900 text-yellow-500{% endif %}">{%
                            if reserva.estado_pago == 'CONFIRMADO' %}Confirmado{% elif reserva.estado_pago ==
                            'EN_REVISION' %}En Revision{% else %}Pendiente{% endif %}</span>'''

new_span = '''<span class="px-3 py-1 rounded-full text-xs font-bold {% if reserva.estado_pago == 'CONFIRMADO' %}bg-green-900 text-green-400{% elif reserva.estado_pago == 'EN_REVISION' %}bg-orange-900 text-orange-400{% else %}bg-yellow-900 text-yellow-500{% endif %}">{% if reserva.estado_pago == 'CONFIRMADO' %}Confirmado{% elif reserva.estado_pago == 'EN_REVISION' %}En Revision{% else %}Pendiente{% endif %}</span>'''

content = content.replace(old_span, new_span)

# Fix 3: Arreglar el div de Pago (lineas 121-123) - consolidar en una linea
old_pago = '''<div>Pago: {% if reserva.metodo_pago == 'MP' %}Mercado Pago{% elif reserva.metodo_pago ==
                            'CRYPTO' %}CryptoMarket{% if reserva.crypto_currency %} ({{ reserva.crypto_currency }}){%
                            endif %}{% else %}Crypto (Manual){% endif %}</div>'''

new_pago = '''<div>Pago: {% if reserva.metodo_pago == 'MP' %}Mercado Pago{% elif reserva.metodo_pago == 'CRYPTO' %}CryptoMarket{% if reserva.crypto_currency %} ({{ reserva.crypto_currency }}){% endif %}{% else %}Crypto (Manual){% endif %}</div>'''

content = content.replace(old_pago, new_pago)

with open(filepath, 'w', encoding='utf-8') as f:
    f.write(content)

print("All fixes applied successfully!")

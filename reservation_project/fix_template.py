import os

path = r'booking\templates\booking\admin_panel_v4.html'

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix split-line template tags by removing newlines inside {% %} blocks
# This is a more aggressive fix that consolidates multi-line tags

# Fix the proyecto option that has split endif
content = content.replace(
    """{% if request.GET.proyecto == p.id|stringformat:'s' %}selected{%
                                endif %}""",
    """{% if request.GET.proyecto == p.id|stringformat:'s' %}selected{% endif %}"""
)

# Fix estado_pago options with split endif
content = content.replace(
    """}selected{% endif %}>
                                Pendiente""",
    """}selected{% endif %}>Pendiente"""  
)

content = content.replace(
    """{% if request.GET.estado_pago == 'EN_REVISION' %}selected{% endif
                                %}>En Revision""",
    """{% if request.GET.estado_pago == 'EN_REVISION' %}selected{% endif %}>En Revision"""
)

content = content.replace(
    """{% if request.GET.estado_pago == 'CONFIRMADO' %}selected{% endif
                                %}>Confirmado""",
    """{% if request.GET.estado_pago == 'CONFIRMADO' %}selected{% endif %}>Confirmado"""
)

# Fix metodo_pago options with split endif  
content = content.replace(
    """}selected{% endif %}>Mercado Pago
                            </option>""",
    """}selected{% endif %}>Mercado Pago</option>"""
)

content = content.replace(
    """}selected{% endif %}>Crypto
                            </option>""",
    """}selected{% endif %}>Crypto</option>"""
)

content = content.replace(
    """{% if request.GET.metodo_pago == 'CRYPTO_MANUAL' %}selected{%
                                endif %}>Crypto Manual""",
    """{% if request.GET.metodo_pago == 'CRYPTO_MANUAL' %}selected{% endif %}>Crypto Manual"""
)

with open(path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Template fixed - split lines consolidated!")

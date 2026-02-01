import re

# Fix admin_panel_v6.html
file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_v6.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix all problematic patterns
content = re.sub(r"estado_pago=='", "estado_pago == '", content)
content = re.sub(r"metodo_pago=='", "metodo_pago == '", content)
content = re.sub(r"proyecto==", "proyecto == ", content)
# Fix broken multiline tags
content = re.sub(r'selected\{%\s*\n\s*endif\s*%\}', 'selected{% endif %}', content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Fixed admin_panel_v6.html!")

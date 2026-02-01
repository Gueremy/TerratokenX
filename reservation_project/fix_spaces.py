import re

file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_v4.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Replace all problematic patterns
replacements = [
    (r"estado_pago=='", "estado_pago == '"),
    (r"metodo_pago=='", "metodo_pago == '"),
    (r"proyecto==", "proyecto == "),
    # Also fix broken multiline tags
    (r"\{%\s+endif\s*\n\s*%\}", "{% endif %}"),
    (r"selected\{%\s*\n\s*endif\s*%\}", "selected{% endif %}"),
]

for pattern, replacement in replacements:
    content = re.sub(pattern, replacement, content)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

# Verify
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

if "estado_pago=='" in content:
    print("ERROR: Still has estado_pago=='")
elif "metodo_pago=='" in content:
    print("ERROR: Still has metodo_pago=='")
else:
    print("SUCCESS! All spaces fixed.")

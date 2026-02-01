import re

filepath = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'

with open(filepath, 'r', encoding='utf-8') as f:
    lines = f.readlines()

for i, line in enumerate(lines):
    # Buscamos la línea aproximada con el error
    if "if proyecto and proyecto.id" in line and "p.id" in line:
        # Reemplazamos forzosamente con la versión correcta
        lines[i] = '                                    <option value="{{ p.id }}" {% if proyecto and proyecto.id == p.id %}selected{% endif %}>\n'
        print(f"Fixed line {i+1}")
        break

with open(filepath, 'w', encoding='utf-8') as f:
    f.writelines(lines)

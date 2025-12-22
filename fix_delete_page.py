import re
import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\eliminar_reserva.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

original_content = content

# Fix: Literal Rendering (Newlines in tag)
# Find {{ <newline> reserva.nombre }} and make it {{ reserva.nombre }}
content = re.sub(r'\{\{\s+reserva\.nombre\s+\}\}', '{{ reserva.nombre }}', content)

if content != original_content:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("FIXED: Consolidated tag in eliminar_reserva.html")
else:
    print("NO CHANGES NEEDED: Tag already consolidated.")

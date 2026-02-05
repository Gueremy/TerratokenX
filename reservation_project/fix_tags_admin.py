import re
import os

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_project_form.html'

if os.path.exists(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Fix the broken tag in the icon span
    pattern = r'visibility_off\{%\s+endif %\}'
    fixed_content = re.sub(pattern, 'visibility_off{% endif %}', content)
    
    # Also ensure the if/else for project is clean
    # The error "Invalid block tag on line 438: 'empty'" is often because of a bad {% if %}
    # let's look for common mistakes like {% if ... {% if
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(fixed_content)
    print("Correccion de tags completada.")
else:
    print("Archivo no encontrado.")

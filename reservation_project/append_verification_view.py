
# Script para anexar la nueva vista de verificación al final de views.py
import os

base_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking'
views_path = os.path.join(base_path, 'views.py')
append_path = os.path.join(base_path, 'append_views_verification_final.py')

try:
    with open(views_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Verificar si ya existe para no duplicar
    if 'def verification(' in content:
        print("La vista verification ya existe en views.py.")
    else:
        with open(append_path, 'r', encoding='utf-8') as f_append:
            new_code = f_append.read()
        
        with open(views_path, 'a', encoding='utf-8') as f_views:
            f_views.write('\n\n' + new_code)
            
        print("Vista verification agregada correctamente a views.py.")
        
except Exception as e:
    print(f"Error: {e}")

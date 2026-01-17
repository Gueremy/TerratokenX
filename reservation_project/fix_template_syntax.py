import os
import re

file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Reemplazar '=="' por ' == "' con regex para asegurar espacios
    # Buscamos request.GET.estado_pago=="ALGO"
    # Reemplazamos por request.GET.estado_pago == "ALGO"
    
    new_content = re.sub(r'request\.GET\.estado_pago=="([^"]+)"', r'request.GET.estado_pago == "\1"', content)
    
    # Verificamos si hubo cambios
    if content == new_content:
        print("No se encontraron coincidencias para reemplazar.")
    else:
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Archivo corregido exitosamente.")

except Exception as e:
    print(f"Error: {e}")


import os
import re

# Ruta exacta del archivo
file_path = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\fractionalizer_edit_project.html"

def fix_file():
    if not os.path.exists(file_path):
        print(f"❌ Archivo no encontrado: {file_path}")
        return

    print(f"Leyendo archivo...")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Patrón RegEx para encontrar tags de Django rotos por saltos de línea dentro de atributos HTML
    # Busca: {% if ... [salto de linea] ... %}
    
    # Intento 1: Reparación específica por reemplazo de cadenas conocidas (basado en el error reportado)
    broken_strings = [
        ('{% if not proyecto.gps_data.lat\n                                        %}required{% else %}readonly{% endif %}', 
         '{% if not proyecto.gps_data.lat %}required{% else %}readonly{% endif %}'),
         
        ('{% if not proyecto.gps_data.lat\n                                        %}required{% else %}readonly{% endif %}',
         '{% if not proyecto.gps_data.lat %}required{% else %}readonly{% endif %}'),

        ('{% if not proyecto.spv_legal_name\n                                %}required{% else %}readonly{% endif %}',
         '{% if not proyecto.spv_legal_name %}required{% else %}readonly{% endif %}')
    ]

    fixed_count = 0
    for broken, fixed in broken_strings:
        if broken in content:
            content = content.replace(broken, fixed)
            fixed_count += 1

    # Intento 2: Reparación robusta con RegEx para cualquier etiqueta {% if ... %} rota
    # Esto une líneas dentro de tags {% ... %}
    def cleaner(match):
        return match.group(0).replace('\n', ' ').replace('  ', ' ')

    # Busca bloques {% ... %} que contengan saltos de línea
    content = re.sub(r'\{%[^%]*\n[^%]*%\}', cleaner, content)

    # Guardar
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    
    print(f"✅ Archivo guardado. Se aplicaron correcciones.")

if __name__ == "__main__":
    fix_file()

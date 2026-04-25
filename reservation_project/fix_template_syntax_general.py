
import re

target_file = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\fractionalizer_create_project.html"

def fix_newlines_in_tags(match):
    # match.group(0) es todo el tag encontrado (ej: {% if \n algo %})
    # Reemplazamos todos los saltos de línea y múltiples espacios por un solo espacio
    fixed = re.sub(r'\s+', ' ', match.group(0))
    return fixed

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    print(f"Longitud original: {len(content)}")

    # 1. Arreglar tags de bloque {% ... %} que tengan saltos de línea dentro
    # Buscamos {% seguido de cualquier cosa hasta %}
    # flags=re.DOTALL permite que el punto coincida con newlines, pero aquí usamos [^}] para ser más seguros
    
    # Patrón: {% [contenido con al menos un \n] %}
    pattern_block = re.compile(r'\{%[^%}]*\n[^%}]*%\}')
    
    # Aplicamos la función fix_newlines_in_tags a cada coincidencia
    content_fixed = pattern_block.sub(fix_newlines_in_tags, content)
    
    # 2. Arreglar tags de variable {{ ... }} que tengan saltos de línea dentro
    pattern_var = re.compile(r'\{\{[^}]*\n[^}]*\}\}')
    content_fixed = pattern_var.sub(fix_newlines_in_tags, content_fixed)

    if content != content_fixed:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content_fixed)
        print("✅ Archivo corregido: Se eliminaron saltos de línea dentro de los tags Django.")
    else:
        print("ℹ️ No se encontraron tags rotos (quizás ya estaban corregidos o el regex no coincidió).")
        
        # Fallback manual específico para el caso reportado por si el regex falla
        # <input type="file" name="archivo_propiedad" {% if not form_data.archivo_propiedad_name
        # %}required{% endif %} accept=".pdf"
        
        manual_fix = content.replace("{% if not form_data.archivo_propiedad_name\n                                %}", "{% if not form_data.archivo_propiedad_name %}")
        if manual_fix != content:
            with open(target_file, 'w', encoding='utf-8') as f:
                f.write(manual_fix)
            print("✅ Corrección manual aplicada.")

except Exception as e:
    print(f"❌ Error: {e}")

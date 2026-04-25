
import re

target_file = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\fractionalizer_create_project.html"

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Corregir saltos de línea dentro de {% if ... %} para imagen_portada_name
    # Buscamos el patrón roto específico mostrado en el error
    # Patrón: {% if \n form_data...
    
    # Vamos a usar reemplazos directos de las cadenas rotas que probablemente causan el problema
    # Estas cadenas se basan en cómo se ven en el traceback del error
    
    # Corrección 1: Bloque de Portada
    broken_if_portada = "{% if\n                                    form_data.imagen_portada_name %}"
    fixed_if_portada = "{% if form_data.imagen_portada_name %}"
    
    broken_else_portada = "{% else\n                                    %}Seleccionar archivo{% endif %}"
    fixed_else_portada = "{% else %}Seleccionar archivo{% endif %}"
    
    # Intentamos reemplazar versiones con diferentes indentaciones usando regex
    # Regex para: {% if [espacio/salto] form_data.imagen_portada_name [espacio/salto] %}
    content = re.sub(r'\{%\s*if\s+form_data\.imagen_portada_name\s*%\s*', '{% if form_data.imagen_portada_name %}', content)
    
    # Regex para: {{ form_data.imagen_portada_name }} [espacio/salto] {% else [espacio/salto] %}
    content = re.sub(r'\{\{\s*form_data\.imagen_portada_name\s*\}\}\s*\{%\s*else\s*%\s*', '{{ form_data.imagen_portada_name }}{% else %}', content)
    
    # Regex para corrección general de saltos de línea malos en tags simples
    # content = re.sub(r'\{%\s*else\s*\n\s*%\}', '{% else %}', content)

    # También revisemos el bloque de archivo_propiedad que seguramente tiene el mismo problema
    content = re.sub(r'\{%\s*if\s+form_data\.archivo_propiedad_name\s*%\s*', '{% if form_data.archivo_propiedad_name %}', content)
    content = re.sub(r'\{\{\s*form_data\.archivo_propiedad_name\s*\}\}\s*\{%\s*else\s*%\s*', '{{ form_data.archivo_propiedad_name }}{% else %}', content)
    content = re.sub(r'Arrastra o haz clic\s*\{%\s*endif\s*%\s*', 'Arrastra o haz clic{% endif %}', content)

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("✅ Archivo corregido (saltos de línea en tags eliminados).")

except Exception as e:
    print(f"❌ Error: {e}")

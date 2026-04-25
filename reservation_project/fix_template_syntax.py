
import os

target_file = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\fractionalizer_create_project.html"

# Mapeo de errores a correcciones
replacements = {
    "form_data.tipo=='Terreno'": "form_data.tipo == 'Terreno'",
    "form_data.tipo=='Departamento'": "form_data.tipo == 'Departamento'",
    "form_data.tipo=='Casa'": "form_data.tipo == 'Casa'",
    "form_data.tipo=='Campo'": "form_data.tipo == 'Campo'",
    "form_data.tipo=='Negocio'": "form_data.tipo == 'Negocio'",
    # Versiones con comillas simples invertidas por si acaso
    'form_data.tipo=="Terreno"': 'form_data.tipo == "Terreno"',
    'form_data.tipo=="Departamento"': 'form_data.tipo == "Departamento"',
    'form_data.tipo=="Casa"': 'form_data.tipo == "Casa"',
    'form_data.tipo=="Campo"': 'form_data.tipo == "Campo"',
    'form_data.tipo=="Negocio"': 'form_data.tipo == "Negocio"',
}

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()
    
    original_content = content
    for wrong, right in replacements.items():
        content = content.replace(wrong, right)
    
    if content != original_content:
        with open(target_file, 'w', encoding='utf-8') as f:
            f.write(content)
        print("✅ Archivo corregido exitosamente via Python.")
    else:
        print("ℹ️ No se encontraron patrones erróneos (quizás ya estaban corregidos).")

except Exception as e:
    print(f"❌ Error al procesar el archivo: {e}")

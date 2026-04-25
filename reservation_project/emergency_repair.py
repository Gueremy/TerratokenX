import os
import re

def emergency_repair():
    template_dir = os.path.join(os.getcwd(), 'booking', 'templates')
    print(f"🚑 Iniciando reparación de emergencia en: {template_dir}")
    
    # Patrón para encontrar etiquetas que se rompieron (ej: espacios raros o escapes)
    # Buscamos asegurar que {{proyecto.campo}} esté limpio
    
    for root, dirs, files in os.walk(template_dir):
        for file in files:
            if file.endswith('.html'):
                file_path = os.path.join(root, file)
                changed = False
                
                with open(file_path, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                
                # 1. Quitar posibles escapes de llaves si el script previo metió algo raro
                new_content = content
                
                # 2. Normalizar etiquetas de variables (asegurar un solo espacio o cero, pero no caracteres raros)
                # Esto arregla {{ proyecto.ubicacion }} y similares
                new_content = re.sub(r'\{\{\s+', '{{ ', new_content)
                new_content = re.sub(r'\s+\}\}', ' }}', new_content)
                
                # 3. Arreglo específico para el error de renderizado visto en capturas
                # Si el motor no las pesca, a veces es por caracteres invisibles (Zwnbsp)
                new_content = new_content.replace('\ufeff', '') 
                
                if new_content != content:
                    with open(file_path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"  ✅ Reparado: {os.path.basename(file_path)}")

if __name__ == "__main__":
    emergency_repair()

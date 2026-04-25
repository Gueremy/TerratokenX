
import os
import re

def fix_rendering_issues():
    # Abarcamos TODO el directorio de templates
    base_dir = r'booking/templates/booking'
    
    print(f"🚀 Iniciando reparación masiva de TODOS los plantillas en: {base_dir}")
    
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        content = f.read()
                    
                    original_content = content
                    
                    # 1. Arreglar {{ variable|filtro }} con saltos de línea
                    # Encuentra {{ algo }} donde 'algo' tiene saltos de linea
                    content = re.sub(
                        r'\{\{(.*?)\}\}', 
                        lambda m: '{{ ' + m.group(1).replace('\n', ' ').replace('\r', '').strip() + ' }}', 
                        content, 
                        flags=re.DOTALL
                    )
                    
                    # 2. Arreglar {% tag ... %} con saltos de línea
                    content = re.sub(
                        r'\{%(.*?)%\}', 
                        lambda m: '{% ' + m.group(1).replace('\n', ' ').replace('\r', '').strip() + ' %}', 
                        content, 
                        flags=re.DOTALL
                    )

                    # 3. Arreglar casos específicos de atributos cortados como class="...
                    # Este es peligroso automatizar, mejor solo tags de django.

                    if content != original_content:
                        with open(path, 'w', encoding='utf-8') as f:
                            f.write(content)
                        print(f"✅ Reparado: {file}")
                    else:
                        pass # Silencioso si no hay cambios
                        
                except Exception as e:
                    print(f"❌ Error leyendo {file}: {e}")

if __name__ == "__main__":
    fix_rendering_issues()

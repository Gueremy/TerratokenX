import os
import re

def fix_profile():
    path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\profile.html'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Fix backslashed quotes and join split tags
    # Also handle the original split version in the user's error report
    text = re.sub(r'{%\s*if\s+profile\.metodo_certificacion\s*==\s*[\\\'"]+FIRMA_VIRTUAL[\\\'"]+\s*%}', "{% if profile.metodo_certificacion == 'FIRMA_VIRTUAL' %}", text, flags=re.DOTALL)
    text = re.sub(r'{%\s*if\s+profile\.metodo_certificacion\s*!=\s*[\\\'"]+SMART_CONTRACT[\\\'"]+\s*%}', "{% if profile.metodo_certificacion != 'SMART_CONTRACT' %}", text, flags=re.DOTALL)
    
    # Check for the specific split from the error:
    # {% if
    # profile.metodo_certificacion=='FIRMA_VIRTUAL' %}
    text = re.sub(r'{%\s*if\s*\n\s*profile\.metodo_certificacion\s*==\s*\'FIRMA_VIRTUAL\'\s*%}', "{% if profile.metodo_certificacion == 'FIRMA_VIRTUAL' %}", text, flags=re.MULTILINE)

    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Fixed profile.html')

def fix_catalog():
    path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\catalog.html'
    if not os.path.exists(path):
        print(f"File not found: {path}")
        return
    with open(path, 'r', encoding='utf-8') as f:
        text = f.read()
    
    # Fix the literal tags shown in screenshot
    text = text.replace('{{                 p.nombre }}', '{{ p.nombre }}')
    text = text.replace('{{                     p.tokens_disponibles }}', '{{ p.tokens_disponibles }}')
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(text)
    print('Fixed catalog.html')

def fix_all_broken_chars():
    base_dir = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking'
    patterns = {
        'Ã¡': 'á', 'Ã©': 'é', 'Ã­': 'í', 'Ã³': 'ó', 'Ãº': 'ú', 'Ã±': 'ñ',
        'Ã\xad': 'í', 'CatÃ¡logo': 'Catálogo', 'InversiÃ³n': 'Inversión'
    }
    for root, dirs, files in os.walk(base_dir):
        for file in files:
            if file.endswith('.html'):
                p = os.path.join(root, file)
                with open(p, 'r', encoding='utf-8', errors='ignore') as f:
                    content = f.read()
                new_content = content
                for k, v in patterns.items():
                    new_content = new_content.replace(k, v)
                if new_content != content:
                    with open(p, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f'Fixed chars in: {file}')

fix_profile()
fix_catalog()
fix_all_broken_chars()

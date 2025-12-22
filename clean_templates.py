
import os
import re

files_to_clean = [
    r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_panel.html",
    r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\editar_reserva.html",
    r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\eliminar_reserva.html"
]

def clean_file(path):
    if not os.path.exists(path):
        print(f"Skipping {path}, not found.")
        return

    print(f"Cleaning {os.path.basename(path)}...")
    
    with open(path, 'rb') as f:
        content_bytes = f.read()

    # Decode as utf-8
    content = content_bytes.decode('utf-8')

    # Replace non-breaking spaces with normal spaces
    content = content.replace('\xa0', ' ')
    
    # Replace any potential weird double quotes
    content = content.replace('“', '"').replace('”', '"')
    
    # Ensure braces are standard
    # We can't easily regex replace braces without context, but we can check specifically for the pattern causing issues?
    # Actually, typically rewriting the file is enough to fix BOM issues if handled by python's utf-8
    
    # Let's verify specific tags that are failing
    # {{ reserva.cantidad_tokens }}
    # Remove any excessive whitespace inside braces if it looks weird? 
    # Just normalize spaces inside tags: {{  var  }} -> {{ var }}
    
    # Regex to find tags and clean them
    # pattern: {{ content }}
    def clean_tag(match):
        raw = match.group(0)
        # Strip internal invisible chars
        cleaned = raw.replace('\xa0', ' ')
        return cleaned

    content = re.sub(r'\{\{.*?\}\}', clean_tag, content)
    content = re.sub(r'\{%.*?%\}', clean_tag, content)

    # Write back
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Done.")

for p in files_to_clean:
    clean_file(p)

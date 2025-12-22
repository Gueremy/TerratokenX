
import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'
file_path_orig = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form.html'

def fix_file(path):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Fix the split template tag
        # We look for the exact sequence seen in view_file
        target_split = '${{ precio_base_token|intcomma\n                            }}'
        replacement_tag = '${{ precio_base_token|intcomma }}'
        
        # 2. Add WhatsApp text (predefined message)
        target_wa = 'href="https://wa.me/56928839093"'
        replacement_wa = 'href="https://wa.me/56928839093?text=Hola%2C%20tengo%20una%20duda%20sobre%20TerraTokenX"'

        new_content = content
        
        if target_split in new_content:
            new_content = new_content.replace(target_split, replacement_tag)
            print(f"Fixed split tag in {path}")
        else:
            print(f"Split tag NOT found in {path}. It might be already fixed or different whitespace.")
            
        if target_wa in new_content:
            new_content = new_content.replace(target_wa, replacement_wa)
            print(f"Updated WhatsApp link in {path}")
        else:
            print(f"WhatsApp link NOT found in {path}")

        if new_content != content:
            with open(path, 'w', encoding='utf-8') as f:
                f.write(new_content)
            print(f"Saved changes to {path}")
        else:
            print(f"No changes made to {path}")

    except Exception as e:
        print(f"Error processing {path}: {e}")

fix_file(file_path)
fix_file(file_path_orig)

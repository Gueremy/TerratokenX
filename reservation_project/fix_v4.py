
import os

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'
out_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v4.html'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Simple replacement of the problematic area
    target = 'Inversionista: {{ user.first_name }} {{ user.last_name }} ({{\n                        user.email }})'
    replacement = 'Inversionista: {{ user.email }}'
    
    if target in content:
        new_content = content.replace(target, replacement)
        print("Replacement found and applied (exact match)")
    else:
        # Try a more fuzzy match
        import re
        pattern = r'Inversionista: \{\{ user\.first_name \}\} \{\{ user\.last_name \}\} \(\{\{\s*user\.email \}\}\)'
        new_content, count = re.subn(pattern, replacement, content)
        if count > 0:
            print(f"Replacement applied via regex ({count} matches)")
        else:
            print("Could not find the target string exactly or via regex.")
            # Let's try to find just the broken part
            pattern2 = r'Inversionista:.*?\(\{\{\s*user\.email \}\}\)'
            new_content, count = re.subn(pattern2, replacement, content, flags=re.DOTALL)
            if count > 0:
                print(f"Replacement applied via fuzzy regex ({count} matches)")
            else:
                print("FATAL: Target string not found at all.")
                exit(1)

    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Successfully created {out_path}")

except Exception as e:
    print(f"Error: {e}")

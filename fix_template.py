
import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # The exact string we are looking for based on previous view_file
    target_split = '${{ precio_base_token|intcomma\n                            }}'
    replacement = '${{ precio_base_token|intcomma }}'

    if target_split in content:
        new_content = content.replace(target_split, replacement)
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("Successfully replaced content.")
    else:
        print("Target string not found. Dumping a snippet to check:")
        start_index = content.find('precio-unitario')
        if start_index != -1:
            print(content[start_index:start_index+200])
        else:
            print("Could not find anchor 'precio-unitario'")

except Exception as e:
    print(f"Error: {e}")

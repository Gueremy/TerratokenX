
import os

file_users = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin\users.html'
file_base = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin\base_admin.html'

def fix_newlines(path, target_start, target_end):
    try:
        with open(path, 'r', encoding='utf-8') as f:
            content = f.read()
        
        # Replace the specific multiline pattern with single line
        # Logic: Find {{ ... \n ... }} and make it {{ ... }}
        
        # Simple string replacement for specific known bad strings
        bad_users = '{{ total_usuarios\n                    }}'
        good_users = '{{ total_usuarios }}'
        
        bad_base = '{{\n                    pending_count }}'
        good_base = '{{ pending_count }}'
        
        # Also try variations of whitespace just in case
        import re
        
        # Fix users.html
        if 'total_usuarios' in content:
            # Regex to find {{ total_usuarios \s+ }}
            content = re.sub(r'\{\{\s*total_usuarios\s*\}\}', '{{ total_usuarios }}', content) 
            # Force replace explicit pattern seen in view_file
            content = content.replace('{{ total_usuarios\n                    }}', '{{ total_usuarios }}')
            
        # Fix base_admin.html
        if 'pending_count' in content:
            content = content.replace('{{\n                    pending_count }}', '{{ pending_count }}')
            content = re.sub(r'\{\{\s*pending_count\s*\}\}', '{{ pending_count }}', content)

        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"Fixed {path}")
        
    except Exception as e:
        print(f"Error fixing {path}: {e}")

print("Fixing files...")
fix_newlines(file_users, 'total', 'usuarios')
fix_newlines(file_base, 'pending', 'count')

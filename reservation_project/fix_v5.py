
import os

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'
out_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v5.html'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix the investor tag
    # The split pattern found in v2:
    # <p class="text-xs text-gray-500">Inversionista: {{ user.first_name }} {{ user.last_name }} ({{
    #                     user.email }})</p>
    
    import re
    investor_pattern = r'Inversionista: \{\{ user\.first_name \}\} \{\{ user\.last_name \}\} \(\{\{\s*user\.email \}\}\)'
    content = re.sub(investor_pattern, 'Inversionista: {{ user.first_name }} {{ user.last_name }} ({{ user.email }})', content, flags=re.DOTALL)
    
    # 2. Fix the syntax error in the project select dropdown
    # Error: 'proyecto.id==p.id' -> Needs spaces 'proyecto.id == p.id'
    syntax_error_pattern = r'proyecto\.id==p\.id'
    content = content.replace('proyecto.id==p.id', 'proyecto.id == p.id')
    
    # Also check if there are other occurrences of missing spaces in comparison
    content = content.replace('==', ' == ')
    # Clean up double spaces if we created them (e.g. ' == ' -> ' == ')
    content = content.replace('  ==  ', ' == ')
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully created {out_path} with fixes.")

except Exception as e:
    print(f"Error: {e}")

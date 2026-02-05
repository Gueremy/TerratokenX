
import os
import re

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v6.html'
out_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v7.html'

try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Remove the Commission Row HTML
    # We'll just comment it out or remove it to be clean.
    # Pattern: <div id="row-comision".*?</div> (dotall)
    row_comision_pattern = r'<div id="row-comision".*?</div>'
    content = re.sub(row_comision_pattern, '', content, flags=re.DOTALL)

    # 2. Kill the commission calculation in JS
    # Look for: commissionAmount = total * 0.0319;
    # Replace with: commissionAmount = 0;
    
    # We need to be careful with the exact string matches
    content = content.replace('commissionAmount = total * 0.0319;', 'commissionAmount = 0;')
    
    # Also disable showing the row in JS just in case
    # if (rowComision) { rowComision.classList.remove('hidden'); ... }
    # We can just leave commissionAmount as 0, and if the row element is missing (deleted above), the JS might error if we don't handle the null check.
    # The JS has `const rowComision = document.getElementById('row-comision');`
    # If I delete the element, `rowComision` will be null.
    # The code says `if (rowComision) { ... }`. So if it's null, it won't crash. Safe.
    
    with open(out_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"Successfully created {out_path} with commission logic removed.")

except Exception as e:
    print(f"Error: {e}")

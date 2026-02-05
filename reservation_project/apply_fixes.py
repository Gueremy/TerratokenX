
import os

views_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\views.py'
sales_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin\sales.html'

# 1. Fix Views.py
with open(views_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Strip unnecessary spaces at the end
    line = line.rstrip() + '\n'
    
    # Fix the extra space in line 347 (index 346)
    if line_num == 347:
        if line.startswith('                 '): # 17 spaces
            new_lines.append('                ' + line.lstrip())
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(views_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

# 2. Fix Sales.html
with open(sales_path, 'r', encoding='utf-8') as f:
    content = f.read()

# Update the condition to handle both CRYPTO and CRYPTO_MANUAL
old_cond = "{% elif reserva.metodo_pago == 'CRYPTO' %}"
new_cond = "{% elif reserva.metodo_pago == 'CRYPTO' or reserva.metodo_pago == 'CRYPTO_MANUAL' %}"

if old_cond in content:
    content = content.replace(old_cond, new_cond)
    with open(sales_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print("Sales.html updated to handle CRYPTO_MANUAL.")
else:
    print("Condition not found in Sales.html.")

print("Corrections applied via script.")

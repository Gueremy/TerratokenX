
import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\views.py'

with open(file_path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

new_lines = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Fix lines 312 to 347 (over-indented 16 instead of 8)
    if 312 <= line_num <= 347:
        if line.startswith('                '): # 16 spaces
            new_lines.append(line[8:])
        else:
            new_lines.append(line)
    # Fix lines 353 to 472 (over-indented 16 instead of 8)
    elif 353 <= line_num <= 472:
        if line.startswith('                '): # 16 spaces
            new_lines.append(line[8:])
        else:
            new_lines.append(line)
    else:
        new_lines.append(line)

with open(file_path, 'w', encoding='utf-8') as f:
    f.writelines(new_lines)

print("Views.py indentation fixed via script.")


import os

path = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\user_dashboard.html"

with open(path, 'r', encoding='utf-8') as f:
    content = f.read()

# Fix the specific syntax error: != 'PENDING' without space
new_content = content.replace("!='PENDING'", "!= 'PENDING'")

if content != new_content:
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Fixed syntax error in user_dashboard.html")
else:
    print("No changes needed (or pattern not found exactly as expected).")

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\verification.html'
with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

new_content = content.replace("url 'projects'", "url 'investor_catalog'")

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(new_content)

print("Template verification.html updated successfully.")

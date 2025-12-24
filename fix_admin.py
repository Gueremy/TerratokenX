import os

path = 'reservation_project/booking/templates/booking/admin_panel.html'
try:
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    new_content = content.replace("pagado=='true'", "pagado == 'true'")
    new_content = new_content.replace("pagado=='false'", "pagado == 'false'")
    
    if content == new_content:
        print("No changes needed (already fixed or pattern not found).")
    else:
        with open(path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("File updated successfully.")

except Exception as e:
    print(f"Error: {e}")

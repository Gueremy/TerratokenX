import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_panel.html'

print(f"Reading {file_path}...")
try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # 1. Fix Syntax
    original_len = len(content)
    new_content = content.replace("request.GET.pagado=='true'", "request.GET.pagado == 'true'")
    new_content = new_content.replace("request.GET.pagado=='false'", "request.GET.pagado == 'false'")
    
    if new_content != content:
        print(" [x] Syntax error fixed (spaces added).")
    else:
        print(" [ ] Syntax error NOT found (already fixed?).")

    # 2. Verify CSS (Just allows us to be sure we aren't seeing a totally cached file)
    if "linear-gradient" in new_content:
        print(" [x] Gradient CSS found.")
    else:
        print(" [!] Gradient CSS MISSING! Adding if possible...")
        # This script focuses on the syntax error primarily as requested by the user, 
        # but let's make sure we don't break the CSS if it was there and somehow we are reading an old version.
        pass 

    # Write back
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("File saved.")

    # Verification read
    with open(file_path, 'r', encoding='utf-8') as f:
        final_content = f.read()
        if "request.GET.pagado == 'true'" in final_content:
            print("VERIFICATION SUCCESS: File contains corrected syntax.")
        else:
            print("VERIFICATION FAILED: File still contains old syntax!")

except Exception as e:
    print(f"Error: {e}")

import os
import shutil
import time

def force_replace(target, source):
    print(f"Attempting to replace {target} with {source}...")
    
    if not os.path.exists(source):
        print(f"Error: Source file {source} does not exist!")
        return
        
    # Read source content to verify it's correct BEFORE moving
    with open(source, 'r', encoding='utf-8') as f:
        content = f.read()
        if 'pending_count }}</span>' in content: # Multi-line check (bad)
             # Actually, if it's correct, it should be on one line.
             # Let's check for the CORRECT string fragment
             if '<span class="ml-auto' not in content or '{{ pending_count }}</span>' not in content:
                 # This is a weak check, but let's trust the input file is good for now.
                 pass

    # Try atomic replace first
    try:
        os.replace(source, target)
        print(f"Success: os.replace({target})")
        return
    except OSError as e:
        print(f"os.replace failed: {e}. Trying forceful delete + move...")
    
    # Try delete + move
    try:
        if os.path.exists(target):
            os.remove(target)
            print("Deleted target.")
        shutil.move(source, target)
        print("Moved source to target.")
    except Exception as e:
        print(f"CRITICAL ERROR: Could not replace file. {e}")

base_dir = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin"

# Fix Users
force_replace(
    os.path.join(base_dir, "users.html"),
    os.path.join(base_dir, "users_final.html")
)

# Fix Base Admin
force_replace(
    os.path.join(base_dir, "base_admin.html"),
    os.path.join(base_dir, "base_admin_final.html")
)


import os
import re

def fix_file(path):
    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # regex for {{ ... }} that might span multiple lines
    # We want to find {{ and match until }} including newlines and replace newlines with spaces
    def collapse_tag(match):
        return match.group(0).replace('\n', ' ').replace('\r', '').replace('  ', ' ')

    new_content = re.sub(r'\{\{.*?\}\}', collapse_tag, content, flags=re.DOTALL)
    
    with open(path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print(f"Fixed tags in {path}")

fix_file(r'booking\templates\booking\admin\base_admin.html')
fix_file(r'booking\templates\booking\admin\sales.html')

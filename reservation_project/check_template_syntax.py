import re
import os

def check_tags(path):
    if not os.path.exists(path):
        return f"{path} not found"
    with open(path, 'r', encoding='utf-8') as f:
        c = f.read()
    
    tags = re.findall(r'\{%\s+(\w+)', c)
    stack = []
    errors = []
    for tag in tags:
        if tag in ['if', 'for', 'block', 'with', 'cache', 'spaceless']:
            stack.append(tag)
        elif tag.startswith('end'):
            expected = tag[3:]
            if not stack:
                errors.append(f"Unexpected {{% {tag} %}}")
            elif stack[-1] != expected:
                errors.append(f"Expected {{% end{stack[-1]} %}}, got {{% {tag} %}}")
            else:
                stack.pop()
    
    if stack:
        errors.append(f"Unclosed tags: {stack}")
    return errors if errors else "OK"

print("Base Admin:", check_tags(r'booking\templates\booking\admin\base_admin.html'))
print("Users V3:", check_tags(r'booking\templates\booking\admin\users_v3.html'))

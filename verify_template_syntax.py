
import re

def verify_file(path):
    print(f"Verifying {path}...")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            lines = f.readlines()
    except Exception as e:
        print(f"Error reading file: {e}")
        return

    stack = []
    
    # Simple regex to find block tags
    # We care about: if, for, while, block, with
    # And their end counterparts
    
    tag_pattern = re.compile(r'{%\s*(if|for|block|with|while)\s+.*?%}|{%\s*(endif|endfor|endblock|endwith|endwhile)\s*%}')
    
    for i, line in enumerate(lines):
        line_num = i + 1
        matches = tag_pattern.finditer(line)
        for match in matches:
            tag_text = match.group(0)
            tag_type = match.group(1) if match.group(1) else match.group(2)
            
            # print(f"Line {line_num}: Found {tag_type} in {tag_text}")

            if tag_type in ['if', 'for', 'block', 'with', 'while']:
                stack.append((tag_type, line_num))
            elif tag_type in ['endif', 'endfor', 'endblock', 'endwith', 'endwhile']:
                if not stack:
                    print(f"ERROR: Found {tag_type} at line {line_num} but stack is empty!")
                    return
                
                last_tag, last_line = stack.pop()
                expected_end = 'end' + last_tag
                
                if tag_type != expected_end:
                    print(f"ERROR: Mismatch! Found {tag_type} at line {line_num}, but expected {expected_end} (opened at line {last_line})")
                    return

    if stack:
        print("ERROR: Unclosed tags remaining:")
        for tag, line in stack:
            print(f"  {tag} opened at line {line}")
    else:
        print("SUCCESS: All block tags verify correctly.")

verify_file(r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_panel.html")

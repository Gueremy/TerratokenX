import re

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_project_form.html'

with open(path, 'r', encoding='utf-8') as f:
    lines = f.readlines()

stack = []
for i, line in enumerate(lines):
    line_num = i + 1
    # Find all if, elif, else, endif, for, empty, endfor
    tags = re.findall(r'\{% (if|elif|else|endif|for|empty|endfor)', line)
    for tag in tags:
        if tag == 'if':
            stack.append(('if', line_num))
        elif tag == 'for':
            stack.append(('for', line_num))
        elif tag == 'endif':
            if not stack or stack[-1][0] not in ['if', 'elif', 'else']:
                print(f"Error: endif at line {line_num} has no matching if. Current stack: {stack}")
            else:
                while stack and stack[-1][0] in ['elif', 'else']:
                    stack.pop()
                if stack and stack[-1][0] == 'if':
                    stack.pop()
        elif tag == 'endfor':
            if not stack or stack[-1][0] not in ['for', 'empty']:
                print(f"Error: endfor at line {line_num} has no matching for. Current stack: {stack}")
            else:
                while stack and stack[-1][0] == 'empty':
                    stack.pop()
                if stack and stack[-1][0] == 'for':
                    stack.pop()
        elif tag == 'elif' or tag == 'else':
             # elif/else don't pop until endif, but they must be inside an if
             pass
        elif tag == 'empty':
             # empty must be inside a for
             pass

print("Final Stack:", stack)

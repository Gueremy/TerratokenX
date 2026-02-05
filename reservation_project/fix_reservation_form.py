
import os

source_path = os.path.join(os.getcwd(), 'booking', 'templates', 'booking', 'reservation_form_v2.html')
dest_path = os.path.join(os.getcwd(), 'booking', 'templates', 'booking', 'reservation_form_v3.html')

print(f"Reading from {source_path}")

try:
    with open(source_path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # We want to fix the split lines for the investor info.
    # We'll traverse the lines and merge them if we find the split pattern.
    
    lines = content.splitlines()
    new_lines = []
    skip_next = False
    
    fixed_count = 0
    
    for i, line in enumerate(lines):
        if skip_next:
            skip_next = False
            continue
            
        # Check for the line containing "Inversionista:" that ends with open parenthesis and braces
        if 'Inversionista: {{ user.first_name }}' in line and line.strip().endswith('({{'):
            # Check if next line completes it
            if i + 1 < len(lines) :
                next_line = lines[i+1]
                if 'user.email' in next_line and '}})' in next_line:
                    # Construct the fixed line
                    # Preserve indentation of the first line
                    indent = line[:line.find('<')] if '<' in line else ''
                    fixed_line = indent + '<p class="text-xs text-gray-500">Inversionista: {{ user.first_name }} {{ user.last_name }} ({{ user.email }})</p>'
                    new_lines.append(fixed_line)
                    skip_next = True
                    fixed_count += 1
                    print(f"Fixed split tag at line {i+1}")
                    continue
        
        new_lines.append(line)
        
    new_content = '\n'.join(new_lines)
    
    with open(dest_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
        
    print(f"Successfully wrote {dest_path} with {fixed_count} fixes.")

except Exception as e:
    print(f"Error: {e}")

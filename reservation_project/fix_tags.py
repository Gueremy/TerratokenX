import os
import re

def fix_html_files(directory):
    # Regex to find {{ ... }} and {% ... %} that might contain newlines
    # We use a non-greedy match that spans multiple lines
    double_brace_pattern = re.compile(r'\{\{.*?\}\}', re.DOTALL)
    percent_tag_pattern = re.compile(r'\{%.*?%\}', re.DOTALL)

    for root, dirs, files in os.walk(directory):
        for file in files:
            if file.endswith('.html'):
                path = os.path.join(root, file)
                with open(path, 'r', encoding='utf-8') as f:
                    content = f.read()

                def remove_newlines(match):
                    return match.group(0).replace('\n', ' ').replace('\r', ' ').replace('  ', ' ')

                new_content = double_brace_pattern.sub(remove_newlines, content)
                new_content = percent_tag_pattern.sub(remove_newlines, new_content)

                if new_content != content:
                    with open(path, 'w', encoding='utf-8') as f:
                        f.write(new_content)
                    print(f"Fixed tags in: {path}")

if __name__ == "__main__":
    template_dir = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates'
    fix_html_files(template_dir)

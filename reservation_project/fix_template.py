import pathlib
import re

file_path = pathlib.Path('booking/templates/booking/admin_panel_v3.html')
content = file_path.read_text(encoding='utf-8')

# Fix 1: split endif tag
pattern1 = r"check_circle\{%\s*\n\s*endif\s*%\}"
replacement1 = "check_circle{% endif %}"
content = re.sub(pattern1, replacement1, content)

# Fix 2: comparison operators need spaces
# Fix request.GET.pagado=='true' -> request.GET.pagado == 'true'
content = content.replace("request.GET.pagado=='true'", "request.GET.pagado == 'true'")
content = content.replace("request.GET.pagado=='false'", "request.GET.pagado == 'false'")

# Write back
file_path.write_text(content, encoding='utf-8')
print("Fixed all template issues!")

# Verify
new_content = file_path.read_text(encoding='utf-8')
issues = []
if "check_circle{%" in new_content and "endif" in new_content[new_content.find("check_circle{%"):new_content.find("check_circle{%")+100]:
    issues.append("Split endif still present")
if "pagado=='" in new_content:
    issues.append("Comparison operators still need spaces")

if issues:
    print("WARNING:", issues)
else:
    print("All fixes verified successfully!")

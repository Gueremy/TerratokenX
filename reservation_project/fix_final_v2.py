
import os
import re

BASE_DIR = os.getcwd()
TEMPLATE_DIR = os.path.join(BASE_DIR, 'booking', 'templates', 'booking')
ADMIN_DIR = os.path.join(TEMPLATE_DIR, 'admin')

# 1. FIX SALES.HTML (Missing Crypto Type)
def fix_sales_html():
    path = os.path.join(ADMIN_DIR, 'sales.html')
    # If file is empty or missing, we can provide a default, but better to edit existing if possible
    # to preserve structure.
    if not os.path.exists(path) or os.path.getsize(path) < 100:
        print("Sales html is empty, skipping patch/restoring default...")
        # (Content would go here if we were restoring from scratch, but let's assume it exists per verify)
        return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()

    # Locate the Crypto Badge and add currency
    # Look for: <span class="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs">Crypto</span>
    target = '<span class="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs">Crypto</span>'
    replacement = '<span class="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs">Crypto {% if reserva.crypto_currency %}({{ reserva.crypto_currency }}){% endif %}</span>'
    
    if target in content and replacement not in content:
        content = content.replace(target, replacement)
        with open(path, 'w', encoding='utf-8') as f:
            f.write(content)
        print("[FIXED] sales.html crypto display")
    else:
        print("[INFO] sales.html crypto display already present or pattern not found")

# 2. RESTORE ADMIN_PROJECT_FORM.HTML (It is 0 bytes)
def restore_project_form():
    path = os.path.join(TEMPLATE_DIR, 'admin_project_form.html') # Note: View calls 'booking/admin_project_form.html'
    
    content = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Editar Proyecto{% endblock %}
{% block page_title %}{% if proyecto %}Editar {{ proyecto.nombre }}{% else %}Nuevo Proyecto{% endif %}{% endblock %}

{% block content %}
<div class="glass-panel rounded-2xl p-8 max-w-4xl mx-auto border border-gold-500/20 shadow-2xl">
    <form method="POST" enctype="multipart/form-data" class="space-y-8">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Global Info -->
            <div class="space-y-6">
                <h3 class="text-lg font-bold text-gold-500 border-b border-gold-500/20 pb-2">Información Básica</h3>
                
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Nombre del Proyecto</label>
                    <input type="text" name="nombre" value="{{ proyecto.nombre|default:'' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Ubicación</label>
                    <input type="text" name="ubicacion" value="{{ proyecto.ubicacion|default:'' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Precio Token (USD)</label>
                        <input type="number" name="precio_token" value="{{ proyecto.precio_token|default:'100' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Tokens Totales</label>
                        <input type="number" name="tokens_totales" value="{{ proyecto.tokens_totales|default:'1000' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Rentabilidad Estimada</label>
                    <input type="text" name="rentabilidad_estimada" value="{{ proyecto.rentabilidad_estimada|default:'12-18% Anual' }}" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>
            </div>

            <!-- Multimedia & Status -->
            <div class="space-y-6">
                <h3 class="text-lg font-bold text-gold-500 border-b border-gold-500/20 pb-2">Multimedia y Estado</h3>
                
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">URL Imagen Portada (G-Drive/URL)</label>
                    <input type="url" name="imagen_portada_url" value="{{ proyecto.imagen_portada_url|default:'' }}" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none" placeholder="https://...">
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">O Subir Imagen</label>
                    <input type="file" name="imagen_portada" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-2 text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-gold-500 file:text-dark-900">
                </div>

                <div class="p-4 bg-dark-800 rounded-xl border border-gray-700">
                    <label class="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="activo" {% if proyecto.activo|default:True %}checked{% endif %} class="w-5 h-5 accent-gold-500">
                        <span class="text-sm text-white font-medium">Proyecto Activo (Visible en Landing)</span>
                    </label>
                </div>

                <div class="p-4 bg-dark-800 rounded-xl border border-gray-700">
                    <label class="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="financiamiento_activo" {% if proyecto.financiamiento_activo|default:True %}checked{% endif %} class="w-5 h-5 accent-gold-500">
                        <span class="text-sm text-white font-medium">Habilitar Venta de Tokens</span>
                    </label>
                </div>
            </div>
        </div>

        <div class="pt-8 border-t border-gray-800 flex justify-end gap-4">
            <a href="{% url 'admin_projects' %}" class="px-6 py-3 text-gray-400 hover:text-white transition-colors">Cancelar</a>
            <button type="submit" class="px-10 py-3 bg-gold-600 hover:bg-gold-500 text-black font-bold rounded-xl shadow-lg transition-all transform hover:scale-105 active:scale-95">
                GUARDAR PROYECTO
            </button>
        </div>
    </form>
</div>
{% endblock %}
"""
    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[FIXED] admin_project_form.html restored")


# 3. CLEAN SYNTAX FOR USERS.HTML AND SIGNATURES.HTML
def clean_syntax_newlines(path):
    if not os.path.exists(path): return

    with open(path, 'r', encoding='utf-8') as f:
        content = f.read()
    
    # Regex to pull {{ \n var }} into {{ var }}
    # Find {{ followed by whitespace/newlines, then capture content, then whitespace/newlines, then }}
    
    # fix {{ ... }}
    content = re.sub(r'\{\{\s*\n+\s*(.*?)\s*\n+\s*\}\}', r'{{\1}}', content, flags=re.DOTALL)
    # Also handle leading newline only: {{ \n var }}
    content = re.sub(r'\{\{\s*\n+\s*(.*?)\s*\}\}', r'{{\1}}', content, flags=re.DOTALL)
    # Also handle trailing newline only: {{ var \n }}
    content = re.sub(r'\{\{\s*(.*?)\s*\n+\s*\}\}', r'{{\1}}', content, flags=re.DOTALL)
    
    # Just to be safe, specific fix for the user report:
    content = content.replace('{{ total_usuarios\n                    }}', '{{ total_usuarios }}')
    content = content.replace('{{ profile.wallet_address\n                    }}', '{{ profile.wallet_address }}')

    with open(path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"[CLEANED] Syntax in {os.path.basename(path)}")
    
# 4. FIX RESERVATION_FORM.HTML (INDEX)
def fix_index_template():
    # Ensure v7 (used by view) matches the known good structure
    path_v7 = os.path.join(TEMPLATE_DIR, 'reservation_form_v7.html')
    path_base = os.path.join(TEMPLATE_DIR, 'reservation_form.html')
    
    if os.path.exists(path_base) and os.path.getsize(path_base) > 0:
        with open(path_base, 'r', encoding='utf-8') as f:
            valid_content = f.read()
        
        with open(path_v7, 'w', encoding='utf-8') as f:
            f.write(valid_content)
        print("[FIXED] Synced reservation_form_v7.html with reservation_form.html")
    else:
        print("[WARN] reservation_form.html is empty/missing, cannot sync v7")

def main():
    fix_sales_html()
    restore_project_form()
    
    clean_syntax_newlines(os.path.join(ADMIN_DIR, 'users.html'))
    clean_syntax_newlines(os.path.join(ADMIN_DIR, 'signatures.html'))
    clean_syntax_newlines(os.path.join(ADMIN_DIR, 'kyc.html'))
    
    fix_index_template()

if __name__ == '__main__':
    main()

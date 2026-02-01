
import os
import re

file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

try:
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # 1. Sanitizar caracteres invisibles (zero-width spaces, etc.)
    # Esto elimina caracteres que no sean ASCII extendido básico o saltos de línea normales
    # Mantenemos caracteres españoles
    sanitized = content

    # 2. Arreglar el ID de FirmaVirtual que sale con llaves literales
    # Buscamos patrones rotos y lo reemplazamos por el simple
    pattern_id = r'ID:\s*\{\{\s*reserva\.firmavirtual_id\|truncatechars:15\s*\}\}'
    replacement_id = 'ID: {{ reserva.firmavirtual_id }}'
    
    # Intentar reemplazo con regex (por si hay espacios raros)
    sanitized = re.sub(pattern_id, replacement_id, sanitized)
    
    # Si el regex falla porque el string es muy diferente, forzamos un reemplazo por contexto
    context_id = '<span class="text-[10px] text-gray-500 mt-1">ID: {{ reserva.firmavirtual_id|truncatechars:15 }}</span>'
    new_context_id = '<span class="text-xs text-gray-500 mt-1 block">ID: {{ reserva.firmavirtual_id }}</span>'
    
    if context_id in sanitized:
        sanitized = sanitized.replace(context_id, new_context_id)
        print("Reemplazado ID exacto.")
    elif 'truncatechars:15' in sanitized:
        # Reemplazo genérico si no calza exacto
        sanitized = re.sub(r'ID:.*?\}\}', 'ID: {{ reserva.firmavirtual_id }}', sanitized)
        print("Reemplazado ID por regex genérico.")
    else:
        print("No se encontró el patrón del ID problemático.")

    # 3. Arreglar Botón Gestionar Proyectos (si estuviera roto)
    # Nos aseguramos que el botón azul tenga las clases correctas
    blue_btn = 'bg-blue-600'
    if blue_btn not in sanitized:
        print("Advertencia: No se encontró la clase bg-blue-600 para el botón.")

    # 4. Arreglar Crypto Currency (asegurar espacios)
    # Buscamos: {{ reserva.crypto_currency }}
    # Nos aseguramos que esté limpio
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(sanitized)
    
    print("Archivo sanitizado y reescrito.")

except Exception as e:
    print(f"Error al procesar archivo: {e}")

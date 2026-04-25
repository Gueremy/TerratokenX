
import re

target_file = r"c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\investor\fractionalizer_create_project.html"

# Clase vieja (variantes comunes)
# Buscaremos cualquier clase que contenga 'bg-dark-900' y 'rounded-lg' para actualizarla
# Pero la estrategia más segura es buscar el patrón `class="..."` dentro de tags input/select/textarea y reemplazar las clases de estilo base

new_style = 'w-full bg-dark-900 border border-gray-600 rounded-xl px-4 py-3 text-white placeholder-gray-500 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all duration-300'

try:
    with open(target_file, 'r', encoding='utf-8') as f:
        content = f.read()

    # Reemplazo 1: Inputs y Selects con el estilo antiguo específico
    # Patrón antiguo típico: rounded-lg px-4 py-2 ... transition-colors
    
    old_style_regex = r'w-full bg-dark-900 border border-gray-600 rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500 transition-colors'
    
    # Reemplagamos ocurrencias directas
    content = content.replace(old_style_regex, new_style)
    
    # Reemplazo 2: Variante con cursor-pointer (para selects)
    old_style_select = old_style_regex + ' cursor-pointer'
    new_style_select = new_style + ' cursor-pointer appearance-none'
    content = content.replace(old_style_select, new_style_select)

    # Reemplazo 3: Variante para Textarea (a veces no tiene todas las clases)
    # Buscamos manualmente donde haya `textarea` y `rounded-lg`
    # Esto es más arriesgado con replace simple, mejor regex si es necesario, pero probemos replace primero.
    
    # Ajuste manual para el textarea de descripción que podría haber quedado fuera
    content = content.replace('rounded-lg px-4 py-2 text-white outline-none focus:border-emerald-500 transition-colors h-32', 'rounded-xl px-4 py-3 text-white placeholder-gray-500 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 transition-all duration-300 h-32')

    with open(target_file, 'w', encoding='utf-8') as f:
        f.write(content)
        
    print("✅ Estilos de inputs actualizados con éxito.")

except Exception as e:
    print(f"❌ Error actualizando estilos: {e}")

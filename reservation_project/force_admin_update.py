import os

# Definir rutas
BASE_DIR = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project'
FILE_PATH = os.path.join(BASE_DIR, 'booking', 'templates', 'booking', 'admin_project_form.html')

# El bloque HTML a inyectar
NEW_BLOCK = """
            <!-- CONFIGURACIÓN DE VENTA (NUEVO BLOQUE UNIFICADO) -->
            <div class="glass-panel rounded-2xl p-6 border border-gold-500/20 mt-6">
                <h3 class="text-lg font-bold text-gold-400 mb-6 flex items-center gap-2">
                    <span class="material-icons">shopping_cart</span> Configuración de Venta
                </h3>

                <div class="space-y-4">
                     <!-- Switch Venta Activa -->
                    <div class="flex items-center gap-3 p-4 bg-dark-800 rounded-xl border border-gray-700">
                        {{ form.financiamiento_activo }}
                        <div>
                            <span class="text-sm font-bold text-white block">Habilitar Venta de Tokens</span>
                            <span class="text-xs text-gray-400">Si está desactivado, el botón de compra no aparecerá.</span>
                        </div>
                    </div>

                    <!-- Switch Cerrojo Drops -->
                    <div class="flex items-center gap-3 p-4 bg-red-500/10 rounded-xl border border-red-500/30 transition-all hover:bg-red-500/20">
                        {{ form.venta_solo_drops }}
                        <div>
                            <span class="text-sm font-bold text-white block flex items-center gap-2">
                                <span class="material-icons text-sm text-red-500">lock</span> Venta solo vía Drops
                            </span>
                            <span class="text-xs text-red-300">Si activas esto, nadie podrá comprar si no hay un Drop activo.</span>
                        </div>
                    </div>
                </div>
            </div>
"""

def apply_patch():
    try:
        with open(FILE_PATH, 'r', encoding='utf-8') as f:
            content = f.read()

        # Verificación de seguridad
        if "Configuración de Venta" in content and "venta_solo_drops" in content:
            print("El bloque ya parece existir en el archivo. No se hicieron cambios.")
            return

        # Puntos de referencia
        marker_start = '<!-- TAB 1: GENERAL -->'
        marker_end = '<!-- TAB 2: TOKENOMICS -->'
        
        # Buscar la sección TAB 1
        pos_start = content.find(marker_start)
        if pos_start == -1:
            print("Error: No se encontró el marcador TAB 1.")
            return

        # Buscar el inicio de TAB 2
        pos_end = content.find(marker_end)
        if pos_end == -1:
            print("Error: No se encontró el marcador TAB 2.")
            return

        # Extraer el contenido entre TAB 1 y TAB 2
        chunk = content[pos_start:pos_end]

        # Encontrar el último cierre de div </div> que cierra el contenedor x-show
        # Y el penúltimo cierre </div> que cierra el glass-panel
        
        # Estrategia más segura: Insertar justo ANTES del </div> que cierra el x-show
        # El x-show envuelve todo el bloque TAB 1.
        # Buscaremos el último </div> en 'chunk'
        
        last_div_index = chunk.rfind('</div>')
        if last_div_index == -1:
            print("Error: Estructura HTML inesperada en TAB 1.")
            return

        # Insertar antes del último div (que es el cierre del x-show)
        new_chunk = chunk[:last_div_index] + NEW_BLOCK + "\n" + chunk[last_div_index:]
        
        # Reconstruir contenido completo
        new_content = content[:pos_start] + new_chunk + content[pos_end:]

        with open(FILE_PATH, 'w', encoding='utf-8') as f:
            f.write(new_content)
            
        print("¡Éxito! Se ha inyectado el bloque de Configuración de Venta en admin_project_form.html.")

    except Exception as e:
        print(f"Error fatal: {e}")

if __name__ == "__main__":
    apply_patch()

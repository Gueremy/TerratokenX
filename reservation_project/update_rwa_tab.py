import os
import re

def update_rwa():
    file_path = os.path.join(os.getcwd(), 'booking', 'templates', 'booking', 'investor', 'fractionalizer_edit_project.html')
    
    print(f"📖 Leyendo: {file_path}")
    with open(file_path, 'r', encoding='utf-8') as f:
        content = f.read()

    # El nuevo contenido HTML para la Tab de Compliance
    new_compliance_html = """
        <!-- TAB 4: COMPLIANCE & RWA (ACTUALIZADO POR SCRIPT) -->
        <div x-show="activeTab === 'compliance'" x-cloak class="space-y-6">
            <div class="glass-panel rounded-2xl p-6 border border-emerald-500/20 relative overflow-hidden">
                <!-- Background Decoration -->
                <div class="absolute top-0 right-0 w-64 h-64 bg-emerald-500/5 rounded-full blur-3xl -translate-y-1/2 translate-x-1/2"></div>

                <h3 class="text-lg font-bold text-emerald-400 mb-8 flex items-center gap-2 border-b border-emerald-500/20 pb-4">
                    <span class="material-icons text-emerald-400">verified_user</span> Datos RWA (Real World Assets)
                </h3>
                
                <div class="grid grid-cols-1 md:grid-cols-2 gap-8 relative z-10 w-full">
                    
                    <!-- COLUMNA 1: DATOS FÍSICOS -->
                    <div class="space-y-6">
                        <div>
                            <label class="block text-xs font-bold text-emerald-400 uppercase tracking-wider mb-3 flex items-center gap-2">
                                <span class="material-icons text-sm text-emerald-400">place</span> Coordenadas GPS (On-Chain)
                            </label>
                            <div class="grid grid-cols-2 gap-3">
                                <div>
                                    <span class="text-[10px] text-gray-500 uppercase mb-1 block">Latitud</span>
                                    <input type="number" step="any" name="gps_lat" 
                                        value="{{ proyecto.gps_data.lat|default:'' }}" 
                                        placeholder="-43.77..."
                                        class="bg-dark-900 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:border-emerald-500 outline-none transition-colors font-mono text-sm">
                                </div>
                                <div>
                                    <span class="text-[10px] text-gray-500 uppercase mb-1 block">Longitud</span>
                                    <input type="number" step="any" name="gps_lng" 
                                        value="{{ proyecto.gps_data.lng|default:'' }}" 
                                        placeholder="-71.69..."
                                        class="bg-dark-900 border border-gray-700 rounded-lg px-3 py-2 text-white w-full focus:border-emerald-500 outline-none transition-colors font-mono text-sm">
                                </div>
                            </div>
                            <p class="text-[10px] text-gray-500 mt-2 flex items-center gap-1">
                                <span class="material-icons text-[10px] text-emerald-400">info</span> Estas coordenadas serán inmutables en Blockchain.
                            </p>
                        </div>

                        <div>
                             <label class="block text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <span class="material-icons text-sm text-emerald-400">business</span> SPV (Sociedad Vehículo)
                            </label>
                            <input type="text" name="spv_legal_name" 
                                value="{{ proyecto.spv_legal_name|default:'' }}"
                                placeholder="Ej: Refugio Patagonia SpA"
                                class="bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-white w-full focus:border-emerald-500 outline-none">
                        </div>
                    </div>

                    <!-- COLUMNA 2: DATOS LEGALES -->
                    <div class="space-y-6">
                        <div>
                            <label class="block text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <span class="material-icons text-sm text-emerald-400">gavel</span> Status Legal
                            </label>
                            <div class="px-4 py-2 rounded-lg bg-dark-900 border border-gray-700 text-gray-300 flex items-center gap-2">
                                {% if proyecto.compliance_status == 'APPROVED' %}
                                    <span class="material-icons text-emerald-500 text-sm">check_circle</span>
                                {% else %}
                                    <span class="material-icons text-yellow-500 text-sm">pending</span> 
                                {% endif %}
                                {{ proyecto.get_compliance_status_display }}
                            </div>
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-emerald-400 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <span class="material-icons text-sm text-emerald-400">folder_open</span> Data Room Link
                            </label>
                            <input type="url" name="data_room_url" 
                                value="{{ proyecto.data_room_url|default:'' }}"
                                placeholder="https://drive.google.com/..."
                                class="bg-dark-900 border border-gray-700 rounded-lg px-4 py-2 text-blue-400 w-full focus:border-emerald-500 outline-none font-mono text-sm">
                        </div>

                        <div>
                            <label class="block text-xs font-bold text-gray-500 uppercase tracking-wider mb-2 flex items-center gap-2">
                                <span class="material-icons text-sm text-emerald-400">fingerprint</span> Legal Hash (SHA-256)
                            </label>
                            <div class="bg-dark-900/50 border border-gray-800 rounded-lg px-3 py-2 text-gray-500 text-[10px] font-mono break-all flex items-center justify-between group">
                                <span>{{ proyecto.legal_hash|default:"Pendiente de generación" }}</span>
                                <span class="material-icons text-[12px] opacity-0 group-hover:opacity-100 cursor-pointer text-emerald-400">content_copy</span>
                            </div>
                        </div>
                    </div>
                </div>
            </div>
        </div>
    """

    # Usamos regex para encontrar el div completo de compliance antiguo
    # Buscamos desde <div x-show="activeTab === 'compliance'" hasta el cierre del div
    # El reto es el anidamiento. Usaremos una aproximación basada en la estructura conocida.
    
    pattern = r'(<!-- TAB 4: COMPLIANCE.*?-->\s*<div x-show="activeTab === \'compliance\'".*?</div>\s*</div>)'
    
    # Intentamos encontrar coincidencia con modo DOTALL
    match = re.search(pattern, content, re.DOTALL)
    
    if match:
        print("✅ Encontrado bloque antiguo de Compliance.")
        new_content = content.replace(match.group(1), new_compliance_html)
        
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(new_content)
        print("🚀 Archivo actualizado exitosamente.")
    else:
        print("⚠️ No se encontró el bloque exacto. Intentando búsqueda más flexible...")
        # Búsqueda más simple por inicio de etiqueta
        start_marker = '<div x-show="activeTab === \'compliance\'"'
        start_idx = content.find(start_marker)
        
        if start_idx != -1:
            # Encontrar el FINAL de este bloque es difícil sin parsear HTML.
            # Pero sabemos que le sigue "<!-- TAB 5" o el fin del form.
            end_marker = '<!-- TAB 5'
            end_idx = content.find(end_marker)
            
            if end_idx != -1:
                print("✅ Encontrado rango entre Tab 4 y Tab 5.")
                # Retroceder un poco para agarrar el comentario <!-- TAB 4...
                comment_start = content.rfind('<!--', 0, start_idx)
                
                final_content = content[:comment_start] + new_compliance_html + "\n\n        " + content[end_idx:]
                with open(file_path, 'w', encoding='utf-8') as f:
                    f.write(final_content)
                print("🚀 Archivo actualizado exitosamente (Método Rango).")
            else:
                print("❌ No se pudo determinar el fin del bloque.")

if __name__ == "__main__":
    update_rwa()

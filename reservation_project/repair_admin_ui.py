import re
import os

path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\admin_project_form.html'

if not os.path.exists(path):
    print("Error: File not found")
    exit(1)

with open(path, 'r', encoding='utf-8') as f:
    c = f.read()

# 1. Cleanup all template tags to avoid line-break syntax errors
c = re.sub(r'\{%\s+', '{% ', c)
c = re.sub(r'\s+%\}', ' %}', c)

# 2. Re-write TAB 4 and TAB 5 to be unified and syntax-valid
tabs_content = """
        <!-- TAB 4: SECTIONS -->
        <div x-show="activeTab === 'sections'" x-cloak class="space-y-6">
            <div class="glass-panel rounded-2xl p-6">
                <div class="flex items-center justify-between mb-8">
                    <h3 class="text-xl font-bold text-gold-400">Secciones Dinámicas</h3>
                    {% if proyecto %}
                    <button type="button"
                        onclick="document.getElementById('newSectionModal').classList.remove('hidden')"
                        class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white rounded-lg text-sm font-bold shadow-lg flex items-center gap-2">
                        <span class="material-icons">add_circle</span> Crear Sección
                    </button>
                    {% else %}
                    <button type="button" disabled
                        class="px-4 py-2 bg-gray-600 text-gray-400 rounded-lg text-sm font-bold cursor-not-allowed flex items-center gap-2">
                        <span class="material-icons text-sm">lock</span> Crear (Guarde primero)
                    </button>
                    {% endif %}
                </div>

                <div class="space-y-3">
                    {% for sec in secciones %}
                    <template id="content-{{ sec.id }}">
                        {{ sec.contenido }}
                    </template>
                    <div class="bg-dark-700/50 p-4 rounded-xl border border-gray-600 hover:border-gold-500/30 transition-all group">
                        <div class="flex items-center justify-between">
                            <div class="flex items-center gap-4">
                                <span class="w-10 h-10 rounded-lg bg-dark-800 flex items-center justify-center text-2xl border border-gray-700">
                                    {{ sec.icono|default:"📄" }}
                                </span>
                                <div>
                                    <h4 class="font-bold text-white text-lg">{{ sec.nombre }}</h4>
                                    <div class="flex items-center gap-3 text-xs text-gray-500 mt-1">
                                        <span class="bg-gray-800 px-2 py-0.5 rounded border border-gray-700">Orden: {{ sec.orden }}</span>
                                        {% if sec.activo %}<span class="text-green-400">Activo</span>{% else %}<span class="text-red-400">Oculto</span>{% endif %}
                                    </div>
                                </div>
                            </div>
                            {% if proyecto %}
                            <div class="flex items-center gap-2 opacity-60 group-hover:opacity-100 transition-opacity">
                                <button type="button"
                                    onclick='openEditModal("{{ sec.id }}", "{{ sec.nombre }}", "{{ sec.icono|default_if_none:"" }}", "{{ sec.orden }}", {{ sec.activo|yesno:"true,false" }})'
                                    class="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/40">
                                    <span class="material-icons">edit</span>
                                </button>
                                <a href="{% url 'section_delete' sec.id %}" onclick="return confirm('¿Eliminar esta sección?')"
                                    class="p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/40">
                                    <span class="material-icons">delete</span>
                                </a>
                            </div>
                            {% endif %}
                        </div>
                    </div>
                    {% empty %}
                    <div class="text-center py-12 border-2 border-dashed border-gray-700 rounded-xl bg-dark-800/50">
                        <span class="material-icons text-4xl text-gray-600 mb-2">view_list</span>
                        <p class="text-gray-400">No hay secciones personalizadas aún.</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>

        <!-- TAB 5: DATA ROOM -->
        <div x-show="activeTab === 'dataroom'" x-cloak class="space-y-6">
            <div class="glass-panel rounded-2xl p-6">
                <div class="flex items-center justify-between mb-6">
                    <h3 class="text-xl font-bold text-gold-400 flex items-center gap-2">
                        <span class="material-icons">folder_special</span>
                        Documentos del Proyecto
                    </h3>
                    {% if proyecto %}
                    <a href="{% url 'proyecto_dataroom' proyecto.slug %}" target="_blank"
                        class="text-sm text-blue-400 hover:text-blue-300 flex items-center gap-1">
                        <span class="material-icons text-sm">open_in_new</span>
                        Ver Data Room público
                    </a>
                    {% endif %}
                </div>

                <!-- Formulario para subir documento -->
                <div class="bg-dark-800 p-4 rounded-xl border border-gray-700 mb-6">
                    <h4 class="text-sm font-semibold text-white mb-4 flex items-center gap-2">
                        <span class="material-icons text-green-400">add_circle</span>
                        Subir Nuevo Documento
                    </h4>
                    {% if proyecto %}
                    <form method="post" enctype="multipart/form-data" action="{% url 'project_edit' proyecto.id %}?upload_doc=1" class="grid grid-cols-1 md:grid-cols-4 gap-4">
                        {% csrf_token %}
                        <input type="hidden" name="upload_document" value="1">
                        <div class="md:col-span-2">
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Título del Documento</label>
                            <input type="text" name="doc_titulo" required placeholder="Ej: Estudio de Títulos" class="w-full bg-dark-900 border border-gray-600 rounded-lg px-3 py-2 text-white focus:border-gold-500 outline-none">
                        </div>
                        <div>
                            <label class="block text-xs font-semibold text-gray-400 uppercase mb-1">Archivo PDF</label>
                            <input type="file" name="doc_archivo" accept=".pdf,.doc,.docx" required class="w-full bg-dark-900 border border-gray-600 rounded-lg px-3 py-2 text-white text-sm file:mr-2 file:py-1 file:px-3 file:rounded file:border-0 file:text-xs file:bg-gold-500 file:text-dark-900 file:font-bold">
                        </div>
                        <div class="flex flex-col justify-end gap-2">
                            <div class="flex items-center gap-4 text-sm">
                                <label class="flex items-center gap-1 text-gray-300"><input type="checkbox" name="doc_publico" class="accent-green-500"><span>Público</span></label>
                                <label class="flex items-center gap-1 text-gray-300"><input type="checkbox" name="doc_nda" class="accent-yellow-500"><span>Req. NDA</span></label>
                            </div>
                            <button type="submit" class="px-4 py-2 bg-green-600 hover:bg-green-500 text-white font-bold rounded-lg text-sm">Subir</button>
                        </div>
                    </form>
                    {% else %}
                    <div class="text-center py-6 bg-dark-900/30 border border-dashed border-gray-700 rounded-xl">
                         <p class="text-gray-500 text-sm">El proyecto debe estar creado para habilitar la subida de archivos.</p>
                    </div>
                    {% endif %}
                </div>

                <!-- Lista de documentos existentes -->
                <div class="space-y-3">
                    {% for doc in proyecto.documentos.all %}
                    <div class="bg-dark-700/50 p-4 rounded-xl border border-gray-600 hover:border-gold-500/30 transition-all flex items-center justify-between">
                        <div class="flex items-center gap-4">
                            <div class="w-10 h-10 rounded-lg flex items-center justify-center {% if doc.requiere_nda %}bg-yellow-500/20{% elif doc.publico %}bg-green-500/20{% else %}bg-gray-500/20{% endif %}">
                                <span class="material-icons {% if doc.requiere_nda %}text-yellow-400{% elif doc.publico %}text-green-400{% else %}text-gray-400{% endif %}">
                                    {% if doc.requiere_nda %}lock{% elif doc.publico %}public{% else %}visibility_off{% endif %}
                                </span>
                            </div>
                            <div>
                                <h4 class="font-medium text-white">{{ doc.titulo }}</h4>
                                <div class="flex items-center gap-3 text-xs text-gray-500 mt-1">
                                    <span>{{ doc.created_at|date:"d M Y" }}</span>
                                    {% if doc.publico %}<span class="bg-green-500/20 text-green-400 px-2 py-0.5 rounded">Público</span>{% endif %}
                                    {% if doc.requiere_nda %}<span class="bg-yellow-500/20 text-yellow-400 px-2 py-0.5 rounded">NDA</span>{% endif %}
                                </div>
                            </div>
                        </div>
                        <div class="flex items-center gap-2">
                            <a href="{{ doc.archivo.url }}" target="_blank" class="p-2 bg-blue-500/20 text-blue-400 rounded-lg hover:bg-blue-500/40"><span class="material-icons text-sm">download</span></a>
                            {% if proyecto %}
                            <form method="post" action="{% url 'project_edit' proyecto.id %}?delete_doc={{ doc.id }}" onsubmit="return confirm('¿Eliminar este documento?')">
                                {% csrf_token %}
                                <input type="hidden" name="delete_document" value="{{ doc.id }}">
                                <button type="submit" class="p-2 bg-red-500/20 text-red-400 rounded-lg hover:bg-red-500/40"><span class="material-icons text-sm">delete</span></button>
                            </form>
                            {% endif %}
                        </div>
                    </div>
                    {% empty %}
                    <div class="text-center py-8 border-2 border-dashed border-gray-700 rounded-xl bg-dark-800/50">
                        <span class="material-icons text-4xl text-gray-600 mb-2">folder_off</span>
                        <p class="text-gray-400">No hay documentos subidos aún</p>
                    </div>
                    {% endfor %}
                </div>
            </div>
        </div>
"""

# Replace the old TAB 4 and TAB 5 content
# It starts at <!-- TAB 4: SECTIONS --> and ends at the end of the form area
pattern = r'<!-- TAB 4: SECTIONS -->.*?<!-- DATA TEMPLATE FOR JS -->'
new_c = re.sub(pattern, tabs_content + "\n    </form>\n</div>\n\n<!-- DATA TEMPLATE FOR JS -->", c, flags=re.DOTALL)

with open(path, 'w', encoding='utf-8') as f:
    f.write(new_c)

print("Repair completed. Tabs 4 and 5 unified and syntax fixed.")

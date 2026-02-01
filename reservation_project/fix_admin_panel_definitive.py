;xzDimport os
import time

file_path = r'c:\proyectos\chelooficial\reservation_project\booking\templates\booking\admin_panel_final.html'

# Contenido CORRECTO y SEGURO
new_content = """{% load humanize %}
<!DOCTYPE html>
<html lang="es">

<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Panel de Administracion</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <style>
        body {
            font-family: Inter, sans-serif;
        }
    </style>
</head>

<body class="bg-gray-900 text-white min-h-screen">
    <nav class="bg-gray-800 border-b border-gray-700 shadow-lg sticky top-0 z-50">
        <div class="container mx-auto px-6 py-4 flex justify-between items-center">
            <span class="text-yellow-400 font-bold text-xl">Panel de Administracion</span>
            <a href="{% url 'logout' %}"
                class="bg-red-600 hover:bg-red-700 text-white px-4 py-2 rounded-lg text-sm">Salir</a>
        </div>
    </nav>
    <div class="container mx-auto px-4 py-8 flex flex-col lg:flex-row gap-8">
        <div class="flex-1 space-y-8">
            {% if messages %}<div class="space-y-4">{% for message in messages %}<div
                    class="p-4 rounded-lg {% if message.tags == 'error' %}bg-red-900 text-red-200{% else %}bg-green-900 text-green-200{% endif %}">
                    {{ message }}</div>{% endfor %}</div>{% endif %}
            <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h2 class="text-lg font-semibold text-yellow-400 mb-4">Filtrar Inversiones</h2>
                <form method="get" class="flex flex-col sm:flex-row gap-4 items-end">
                    <div class="flex-1 w-full">
                        <label class="block text-sm text-gray-400 mb-1">Estado de Pago</label>
                        <select name="estado_pago"
                            class="w-full bg-gray-700 border border-gray-600 rounded-lg p-2.5 text-white">
                            <option value="">Todos</option>
                            <option value="PENDIENTE">Pendiente</option>
                            <option value="EN_REVISION">En Revision</option>
                            <option value="CONFIRMADO">Confirmado</option>
                        </select>
                    </div>
                    <div class="flex gap-2">
                        <a href="{% url 'admin_panel' %}"
                            class="px-4 py-2.5 bg-gray-700 text-white rounded-lg">Limpiar</a>
                        <button type="submit"
                            class="px-6 py-2.5 bg-yellow-500 text-black font-bold rounded-lg">Filtrar</button>
                    </div>
                </form>
            </div>
            
            <!-- FirmaVirtual Dashboard -->
            <div class="bg-gray-800 p-6 rounded-xl border border-gray-700 mb-6">
                <h2 class="text-lg font-semibold text-yellow-400 mb-4 flex items-center gap-2">
                    <span class="material-icons">verified</span>
                    Contratos FirmaVirtual
                </h2>
                <div class="grid grid-cols-2 md:grid-cols-4 gap-4 mb-4">
                    <div class="bg-gray-700 p-4 rounded-lg text-center">
                        <div class="text-2xl font-bold text-white">{{ fv_stats.total|default:0 }}</div>
                        <div class="text-xs text-gray-400 uppercase">Total Enviados</div>
                    </div>
                    <div class="bg-blue-900/50 p-4 rounded-lg text-center border border-blue-700">
                        <div class="text-2xl font-bold text-blue-400">{{ fv_stats.sent|default:0 }}</div>
                        <div class="text-xs text-blue-300 uppercase">Enviados</div>
                    </div>
                    <div class="bg-yellow-900/50 p-4 rounded-lg text-center border border-yellow-700">
                        <div class="text-2xl font-bold text-yellow-400">{{ fv_stats.pending|default:0 }}</div>
                        <div class="text-xs text-yellow-300 uppercase">Pendientes</div>
                    </div>
                    <div class="bg-green-900/50 p-4 rounded-lg text-center border border-green-700">
                        <div class="text-2xl font-bold text-green-400">{{ fv_stats.signed|default:0 }}</div>
                        <div class="text-xs text-green-300 uppercase">Firmados</div>
                    </div>
                </div>
            </div>

            <form method="post" action="{% url 'export_reservas_excel' %}" id="exportForm" class="flex flex-wrap gap-4">
                {% csrf_token %}
                <button type="submit" name="export_excel"
                    class="bg-green-600 text-white px-5 py-2.5 rounded-lg">Exportar a Excel</button>
                <button type="submit" formaction="{% url 'export_reservas_pdf' %}"
                    class="bg-red-600 text-white px-5 py-2.5 rounded-lg">Exportar a PDF</button>
            </form>
            <div class="space-y-4">
                {% for reserva in reservas %}
                <div class="bg-gray-800 border border-gray-700 rounded-xl p-6 relative">
                    <input type="checkbox" name="selected_ids" value="{{ reserva.id }}" form="exportForm" class="absolute top-4 right-4 w-5 h-5">
                    <div class="flex justify-between items-start mb-4 pr-8">
                        <div>
                            <h3 class="text-xl font-bold text-yellow-400">{{ reserva.nombre }}</h3>
                            <span class="text-xs text-gray-500">ID: {{ reserva.numero_reserva }}</span>
                        </div>

                        {% if reserva.estado_pago == 'CONFIRMADO' %}
                        <span class="px-3 py-1 rounded-full text-xs font-bold bg-green-900 text-green-400">Confirmado</span>
                        {% elif reserva.estado_pago == 'EN_REVISION' %}
                        <span class="px-3 py-1 rounded-full text-xs font-bold bg-orange-900 text-orange-400">En Revision</span>
                        {% else %}
                        <span class="px-3 py-1 rounded-full text-xs font-bold bg-yellow-900 text-yellow-500">Pendiente</span>
                        {% endif %}
                    </div>
                    
                    <div class="grid grid-cols-1 md:grid-cols-2 gap-y-3 gap-x-8 text-sm text-gray-300">
                        <div>Fecha: {{ reserva.created_at|date:'d M Y H:i' }}</div>
                        <div>Email: {{ reserva.correo }}</div>
                        <div>Telefono: {{ reserva.telefono }}</div>
                        <div>Direccion: {{ reserva.direccion }}</div>
                        <div>Total: USD {{ reserva.total|floatformat:0 }}</div>
                    </div>

                    {% if reserva.firmavirtual_id %}
                    <div class="mt-3 p-3 bg-gray-700/50 rounded-lg">
                        <div class="flex justify-between items-center">
                            <span class="text-xs text-gray-400">FV ID: {{ reserva.firmavirtual_id|truncatechars:10 }}</span>
                            <span class="text-sm font-bold {% if reserva.firmavirtual_status == 'signed' %}text-green-400{% else %}text-yellow-400{% endif %}">
                                {{ reserva.firmavirtual_status|default:"PENDIENTE"|upper }}
                            </span>
                        </div>
                    </div>
                    {% elif reserva.estado_pago == 'CONFIRMADO' %}
                    <div class="mt-3">
                        <a href="{% url 'reenviar_contrato' reserva.id %}" class="text-xs text-yellow-500 hover:text-yellow-400 underline">
                            Re-enviar Contrato
                        </a>
                    </div>
                    {% endif %}

                    <div class="mt-6 flex gap-3 border-t border-gray-700 pt-4">
                        <a href="{% url 'editar_reserva' reserva.id %}" class="bg-blue-600 text-white px-4 py-2 rounded text-sm">Editar</a>
                        <a href="{% url 'eliminar_reserva' reserva.id %}" class="bg-red-600 text-white px-4 py-2 rounded text-sm">Eliminar</a>
                    </div>
                </div>
                {% endfor %}
                
                {% if not reservas %}
                <div class="text-center py-12 bg-gray-800 rounded-xl">
                    <p class="text-gray-400">No hay inversiones registradas.</p>
                </div>
                {% endif %}
            </div>
        </div>
        
        <!-- Sidebar simple -->
        <div class="w-full lg:w-1/4 space-y-8">
             <div class="bg-gray-800 p-6 rounded-xl border border-gray-700">
                <h3 class="text-lg font-bold text-yellow-400 mb-4">Configuracion</h3>
                <p class="text-gray-400 text-sm">Panel simplificado.</p>
             </div>
        </div>
    </div>
</body>
</html>
"""

try:
    if os.path.exists(file_path):
        os.remove(file_path)
        print("deleted old file")
        time.sleep(1) # wait for system to release
    
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(new_content)
    print("Succesfully rewrote admin_panel_final.html")
except Exception as e:
    print(f"Error: {e}")

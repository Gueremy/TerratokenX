"""
SCRIPT DE REPARACIÓN DE TEMPLATES DEL DASHBOARD
================================================
Ejecutar con: python fix_dashboard_templates.py

Este script elimina y recrea los templates del admin dashboard
para solucionar problemas de corrupción por OneDrive.
"""

import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'booking', 'templates', 'booking', 'admin')

# Asegurar que el directorio existe
os.makedirs(TEMPLATE_DIR, exist_ok=True)

# ============================================
# TEMPLATE 1: dashboard.html
# ============================================
DASHBOARD_CONTENT = '''{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Resumen{% endblock %}
{% block page_title %}Dashboard General{% endblock %}

{% block content %}
<div class="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
    <div class="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform">
        <div class="absolute inset-0 bg-gradient-to-br from-green-500/10 to-emerald-600/10"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-12 h-12 rounded-xl bg-green-500/20 flex items-center justify-center">
                    <span class="material-icons text-green-400 text-2xl">attach_money</span>
                </div>
                <span class="text-xs text-green-400 bg-green-500/20 px-2 py-1 rounded-full">USD</span>
            </div>
            <p class="text-gray-400 text-sm mb-1">Ingresos Totales</p>
            <p class="text-3xl font-bold text-white">${{ kpi.total_revenue|floatformat:0|intcomma }}</p>
        </div>
    </div>

    <div class="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform">
        <div class="absolute inset-0 bg-gradient-to-br from-blue-500/10 to-indigo-600/10"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-12 h-12 rounded-xl bg-blue-500/20 flex items-center justify-center">
                    <span class="material-icons text-blue-400 text-2xl">token</span>
                </div>
            </div>
            <p class="text-gray-400 text-sm mb-1">Tokens Vendidos</p>
            <p class="text-3xl font-bold text-white">{{ kpi.tokens_sold|intcomma }}</p>
        </div>
    </div>

    <div class="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform">
        <div class="absolute inset-0 bg-gradient-to-br from-purple-500/10 to-violet-600/10"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-12 h-12 rounded-xl bg-purple-500/20 flex items-center justify-center">
                    <span class="material-icons text-purple-400 text-2xl">verified</span>
                </div>
                <span class="text-xs text-purple-400 bg-purple-500/20 px-2 py-1 rounded-full">{{ kpi.pending_signatures }} pend.</span>
            </div>
            <p class="text-gray-400 text-sm mb-1">Contratos Firmados</p>
            <p class="text-3xl font-bold text-white">{{ kpi.signed_contracts }}</p>
        </div>
    </div>

    <div class="glass-panel rounded-2xl p-6 relative overflow-hidden group hover:scale-[1.02] transition-transform">
        <div class="absolute inset-0 bg-gradient-to-br from-orange-500/10 to-amber-600/10"></div>
        <div class="relative">
            <div class="flex items-center justify-between mb-4">
                <div class="w-12 h-12 rounded-xl bg-orange-500/20 flex items-center justify-center">
                    <span class="material-icons text-orange-400 text-2xl">apartment</span>
                </div>
            </div>
            <p class="text-gray-400 text-sm mb-1">Proyectos Activos</p>
            <p class="text-3xl font-bold text-white">{{ kpi.projects_active }}</p>
        </div>
    </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-3 gap-6 mb-8">
    <div class="lg:col-span-2 glass-panel rounded-2xl p-6">
        <div class="flex items-center justify-between mb-6">
            <h2 class="text-lg font-semibold text-white flex items-center gap-2">
                <span class="material-icons text-yellow-400">leaderboard</span>
                Top Proyectos por Ventas
            </h2>
            <a href="{% url 'admin_projects' %}" class="text-blue-400 text-sm hover:underline">Ver todos</a>
        </div>
        <div class="overflow-x-auto">
            <table class="w-full">
                <thead>
                    <tr class="text-left text-xs text-gray-500 uppercase border-b border-gray-700">
                        <th class="pb-3 font-medium">Proyecto</th>
                        <th class="pb-3 font-medium">Tokens</th>
                        <th class="pb-3 font-medium">Ingresos</th>
                        <th class="pb-3 font-medium">Progreso</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-800">
                    {% for proyecto in top_projects %}
                    <tr class="hover:bg-gray-800/50">
                        <td class="py-4">
                            <div class="flex items-center gap-3">
                                <div class="w-10 h-10 rounded-lg bg-gradient-to-br from-blue-500 to-purple-600 flex items-center justify-center text-white font-bold">
                                    {{ proyecto.nombre|slice:":1" }}
                                </div>
                                <div>
                                    <p class="font-medium text-white">{{ proyecto.nombre }}</p>
                                    <p class="text-xs text-gray-500">{{ proyecto.ubicacion }}</p>
                                </div>
                            </div>
                        </td>
                        <td class="py-4">
                            <span class="text-white font-semibold">{{ proyecto.tokens_vendidos }}</span>
                            <span class="text-gray-500 text-sm">/ {{ proyecto.tokens_totales }}</span>
                        </td>
                        <td class="py-4 text-green-400 font-semibold">${{ proyecto.ingresos|floatformat:0|intcomma }}</td>
                        <td class="py-4">
                            <div class="w-full bg-gray-700 rounded-full h-2">
                                <div class="h-2 rounded-full bg-gradient-to-r from-blue-500 to-purple-500" style="width: {{ proyecto.porcentaje_vendido }}%"></div>
                            </div>
                            <span class="text-xs text-gray-400">{{ proyecto.porcentaje_vendido }}%</span>
                        </td>
                    </tr>
                    {% empty %}
                    <tr><td colspan="4" class="py-8 text-center text-gray-500">No hay proyectos</td></tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>

    <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <span class="material-icons text-green-400">history</span>
            Actividad Reciente
        </h2>
        <div class="space-y-4">
            {% for venta in recent_sales %}
            <div class="flex items-center gap-4 p-3 rounded-lg bg-gray-800/50 hover:bg-gray-800">
                <div class="w-10 h-10 rounded-full flex items-center justify-center text-sm font-bold bg-gray-500/20 text-gray-400">
                    {{ venta.nombre|slice:":2"|upper }}
                </div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-medium text-white truncate">{{ venta.nombre }}</p>
                    <p class="text-xs text-gray-500">{{ venta.cantidad_tokens }} tokens</p>
                </div>
                <div class="text-right">
                    <p class="text-sm font-semibold text-white">${{ venta.total|floatformat:0 }}</p>
                    <p class="text-[10px] text-gray-500">{{ venta.created_at|timesince }}</p>
                </div>
            </div>
            {% empty %}
            <p class="text-center text-gray-500 py-4">Sin actividad</p>
            {% endfor %}
        </div>
        <a href="{% url 'admin_sales' %}" class="mt-4 block text-center text-blue-400 text-sm hover:underline py-2">Ver todas →</a>
    </div>
</div>

<div class="grid grid-cols-1 lg:grid-cols-2 gap-6">
    <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <span class="material-icons text-purple-400">pie_chart</span>
            Estado de Contratos
        </h2>
        <div class="flex items-center justify-center h-64">
            <canvas id="signaturesChart"></canvas>
        </div>
    </div>

    <div class="glass-panel rounded-2xl p-6">
        <h2 class="text-lg font-semibold text-white mb-6 flex items-center gap-2">
            <span class="material-icons text-purple-400">analytics</span>
            Metricas de Firmas
        </h2>
        <div class="grid grid-cols-2 gap-4">
            <div class="bg-blue-500/10 border border-blue-500/20 rounded-xl p-4 text-center">
                <p class="text-3xl font-bold text-blue-400">{{ signatures_stats.sent|default:0 }}</p>
                <p class="text-sm text-gray-400 mt-1">Enviados</p>
            </div>
            <div class="bg-yellow-500/10 border border-yellow-500/20 rounded-xl p-4 text-center">
                <p class="text-3xl font-bold text-yellow-400">{{ signatures_stats.pending|default:0 }}</p>
                <p class="text-sm text-gray-400 mt-1">Pendientes</p>
            </div>
            <div class="bg-green-500/10 border border-green-500/20 rounded-xl p-4 text-center">
                <p class="text-3xl font-bold text-green-400">{{ signatures_stats.signed|default:0 }}</p>
                <p class="text-sm text-gray-400 mt-1">Firmados</p>
            </div>
            <div class="bg-red-500/10 border border-red-500/20 rounded-xl p-4 text-center">
                <p class="text-3xl font-bold text-red-400">{{ signatures_stats.rejected|default:0 }}</p>
                <p class="text-sm text-gray-400 mt-1">Rechazados</p>
            </div>
        </div>
        <a href="{% url 'admin_signatures' %}" class="mt-6 block w-full text-center bg-purple-600 hover:bg-purple-700 text-white font-medium py-3 rounded-xl">
            Gestionar Firmas
        </a>
    </div>
</div>

<script>
document.addEventListener('DOMContentLoaded', function() {
    var ctx = document.getElementById('signaturesChart').getContext('2d');
    new Chart(ctx, {
        type: 'doughnut',
        data: {
            labels: ['Enviados', 'Pendientes', 'Firmados', 'Rechazados'],
            datasets: [{
                data: [{{ signatures_stats.sent|default:0 }}, {{ signatures_stats.pending|default:0 }}, {{ signatures_stats.signed|default:0 }}, {{ signatures_stats.rejected|default:0 }}],
                backgroundColor: ['#3b82f6', '#eab308', '#22c55e', '#ef4444'],
                borderWidth: 0,
                hoverOffset: 10
            }]
        },
        options: {
            responsive: true,
            maintainAspectRatio: false,
            cutout: '70%',
            plugins: {
                legend: {
                    position: 'bottom',
                    labels: { color: '#9ca3af', padding: 20, usePointStyle: true }
                }
            }
        }
    });
});
</script>
{% endblock %}
'''

# ============================================
# TEMPLATE 2: sales.html
# ============================================
SALES_CONTENT = '''{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Compras Tokens{% endblock %}
{% block page_title %}Gestion de Ventas{% endblock %}

{% block content %}
<div class="glass-panel rounded-2xl p-6 mb-6">
    <form method="get" class="flex flex-col md:flex-row gap-4 items-end">
        <div class="flex-1">
            <label class="block text-xs text-gray-500 uppercase mb-2">Estado de Pago</label>
            <select name="estado_pago" class="w-full bg-gray-800 border border-gray-700 rounded-xl p-3 text-white outline-none">
                <option value="">Todos</option>
                <option value="PENDIENTE">Pendiente</option>
                <option value="EN_REVISION">En Revision</option>
                <option value="CONFIRMADO">Confirmado</option>
            </select>
        </div>
        <div class="flex gap-2">
            <a href="{% url 'admin_sales' %}" class="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl">Limpiar</a>
            <button type="submit" class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl">Filtrar</button>
        </div>
    </form>
</div>

<div class="flex gap-4 mb-6">
    <form method="post" action="{% url 'export_reservas_excel' %}">
        {% csrf_token %}
        <button type="submit" class="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-sm">
            <span class="material-icons text-lg">table_chart</span>Excel
        </button>
    </form>
    <form method="post" action="{% url 'export_reservas_pdf' %}">
        {% csrf_token %}
        <button type="submit" class="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-sm">
            <span class="material-icons text-lg">picture_as_pdf</span>PDF
        </button>
    </form>
</div>

<div class="glass-panel rounded-2xl overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full">
            <thead class="bg-gray-800/50">
                <tr class="text-left text-xs text-gray-400 uppercase">
                    <th class="px-6 py-4 font-medium">Cliente</th>
                    <th class="px-6 py-4 font-medium">Proyecto</th>
                    <th class="px-6 py-4 font-medium">Tokens</th>
                    <th class="px-6 py-4 font-medium">Total</th>
                    <th class="px-6 py-4 font-medium">Metodo</th>
                    <th class="px-6 py-4 font-medium">Estado</th>
                    <th class="px-6 py-4 font-medium">Contrato</th>
                    <th class="px-6 py-4 font-medium text-right">Acciones</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-800">
                {% for reserva in reservas %}
                <tr class="hover:bg-gray-800/30">
                    <td class="px-6 py-4">
                        <p class="font-medium text-white">{{ reserva.nombre }}</p>
                        <p class="text-xs text-gray-500">{{ reserva.correo }}</p>
                    </td>
                    <td class="px-6 py-4 text-gray-300">{{ reserva.proyecto.nombre|default:"-" }}</td>
                    <td class="px-6 py-4 text-white font-semibold">{{ reserva.cantidad_tokens }}</td>
                    <td class="px-6 py-4 text-green-400 font-semibold">${{ reserva.total|floatformat:0|intcomma }}</td>
                    <td class="px-6 py-4">
                        {% if reserva.metodo_pago == 'MP' %}
                        <span class="px-2 py-1 rounded-full bg-blue-500/20 text-blue-400 text-xs">Mercado Pago</span>
                        {% elif reserva.metodo_pago == 'CRYPTO' %}
                        <span class="px-2 py-1 rounded-full bg-orange-500/20 text-orange-400 text-xs">Crypto</span>
                        {% else %}
                        <span class="text-gray-500 text-xs">Manual</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4">
                        {% if reserva.estado_pago == 'CONFIRMADO' %}
                        <span class="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-medium">Confirmado</span>
                        {% elif reserva.estado_pago == 'EN_REVISION' %}
                        <span class="px-3 py-1 rounded-full bg-yellow-500/20 text-yellow-400 text-xs font-medium">En Revision</span>
                        {% else %}
                        <span class="px-3 py-1 rounded-full bg-gray-500/20 text-gray-400 text-xs font-medium">Pendiente</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4">
                        {% if reserva.firmavirtual_id %}
                            {% if reserva.firmavirtual_status == 'signed' %}
                            <span class="text-green-400 text-xs">Firmado</span>
                            {% else %}
                            <span class="text-blue-400 text-xs">Enviado</span>
                            {% endif %}
                        {% elif reserva.estado_pago == 'CONFIRMADO' %}
                        <a href="{% url 'reenviar_contrato' reserva.id %}" class="text-yellow-400 text-xs hover:underline">Re-enviar</a>
                        {% else %}
                        <span class="text-gray-600 text-xs">-</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-2">
                            <a href="{% url 'editar_reserva' reserva.id %}" class="p-2 text-gray-400 hover:text-blue-400 rounded-lg"><span class="material-icons text-lg">edit</span></a>
                            <a href="{% url 'eliminar_reserva' reserva.id %}" class="p-2 text-gray-400 hover:text-red-400 rounded-lg"><span class="material-icons text-lg">delete</span></a>
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="8" class="px-6 py-12 text-center text-gray-500">No hay ventas</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''

# ============================================
# TEMPLATE 3: signatures.html
# ============================================
SIGNATURES_CONTENT = '''{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Firmas Virtuales{% endblock %}
{% block page_title %}Gestion de Contratos{% endblock %}

{% block content %}
<div class="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
    <div class="glass-panel rounded-xl p-4 text-center">
        <p class="text-3xl font-bold text-white">{{ stats.total|default:0 }}</p>
        <p class="text-sm text-gray-400 mt-1">Total Contratos</p>
    </div>
    <div class="glass-panel rounded-xl p-4 text-center border-l-4 border-blue-500">
        <p class="text-3xl font-bold text-blue-400">{{ stats.sent|default:0 }}</p>
        <p class="text-sm text-gray-400 mt-1">Enviados</p>
    </div>
    <div class="glass-panel rounded-xl p-4 text-center border-l-4 border-green-500">
        <p class="text-3xl font-bold text-green-400">{{ stats.signed|default:0 }}</p>
        <p class="text-sm text-gray-400 mt-1">Firmados</p>
    </div>
    <div class="glass-panel rounded-xl p-4 text-center border-l-4 border-red-500">
        <p class="text-3xl font-bold text-red-400">{{ stats.rejected|default:0 }}</p>
        <p class="text-sm text-gray-400 mt-1">Rechazados</p>
    </div>
</div>

<div class="glass-panel rounded-2xl p-6 mb-6">
    <form method="get" class="flex flex-col md:flex-row gap-4 items-end">
        <div class="flex-1">
            <label class="block text-xs text-gray-500 uppercase mb-2">Estado</label>
            <select name="status" class="w-full bg-gray-800 border border-gray-700 rounded-xl p-3 text-white outline-none">
                <option value="">Todos</option>
                <option value="sent">Enviados</option>
                <option value="signed">Firmados</option>
                <option value="rejected">Rechazados</option>
            </select>
        </div>
        <div class="flex gap-2">
            <a href="{% url 'admin_signatures' %}" class="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl">Limpiar</a>
            <button type="submit" class="px-6 py-3 bg-purple-600 hover:bg-purple-700 text-white font-medium rounded-xl">Filtrar</button>
        </div>
    </form>
</div>

<div class="glass-panel rounded-2xl overflow-hidden">
    <div class="overflow-x-auto">
        <table class="w-full">
            <thead class="bg-gray-800/50">
                <tr class="text-left text-xs text-gray-400 uppercase">
                    <th class="px-6 py-4 font-medium">Cliente</th>
                    <th class="px-6 py-4 font-medium">Tipo</th>
                    <th class="px-6 py-4 font-medium">Proyecto</th>
                    <th class="px-6 py-4 font-medium">ID FirmaVirtual</th>
                    <th class="px-6 py-4 font-medium">Estado</th>
                    <th class="px-6 py-4 font-medium">Fecha</th>
                    <th class="px-6 py-4 font-medium text-right">Acciones</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-800">
                {% for contrato in contratos %}
                <tr class="hover:bg-gray-800/30">
                    <td class="px-6 py-4">
                        <p class="font-medium text-white">{{ contrato.nombre }}</p>
                        <p class="text-xs text-gray-500">{{ contrato.correo }}</p>
                    </td>
                    <td class="px-6 py-4">
                        {% if contrato.es_empresa %}
                        <span class="text-purple-400 text-sm">Persona Juridica</span>
                        {% else %}
                        <span class="text-gray-300 text-sm">Persona Natural</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4 text-gray-300">{{ contrato.proyecto.nombre|default:"-" }}</td>
                    <td class="px-6 py-4">
                        <code class="text-xs text-gray-400 bg-gray-800 px-2 py-1 rounded">{{ contrato.firmavirtual_id|truncatechars:20 }}</code>
                    </td>
                    <td class="px-6 py-4">
                        {% if contrato.firmavirtual_status == 'signed' %}
                        <span class="px-3 py-1 rounded-full bg-green-500/20 text-green-400 text-xs font-medium">Firmado</span>
                        {% elif contrato.firmavirtual_status == 'rejected' %}
                        <span class="px-3 py-1 rounded-full bg-red-500/20 text-red-400 text-xs font-medium">Rechazado</span>
                        {% else %}
                        <span class="px-3 py-1 rounded-full bg-blue-500/20 text-blue-400 text-xs font-medium">Enviado</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4 text-gray-400 text-sm">{{ contrato.updated_at|date:"d M Y H:i" }}</td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-2">
                            {% if contrato.contrato_firmado %}
                            <a href="{{ contrato.contrato_firmado.url }}" target="_blank" class="p-2 text-green-400 hover:bg-green-500/10 rounded-lg"><span class="material-icons text-lg">download</span></a>
                            {% endif %}
                            {% if contrato.firmavirtual_status != 'signed' %}
                            <a href="{% url 'reenviar_contrato' contrato.id %}" class="p-2 text-yellow-400 hover:bg-yellow-500/10 rounded-lg"><span class="material-icons text-lg">refresh</span></a>
                            {% endif %}
                            <a href="{% url 'editar_reserva' contrato.id %}" class="p-2 text-gray-400 hover:text-blue-400 rounded-lg"><span class="material-icons text-lg">visibility</span></a>
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" class="px-6 py-12 text-center text-gray-500">No hay contratos</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''

# ============================================
# EJECUTAR REPARACIÓN
# ============================================
def main():
    files = {
        'dashboard.html': DASHBOARD_CONTENT,
        'sales.html': SALES_CONTENT,
        'signatures.html': SIGNATURES_CONTENT,
    }
    
    for filename, content in files.items():
        filepath = os.path.join(TEMPLATE_DIR, filename)
        
        # Eliminar archivo si existe
        if os.path.exists(filepath):
            os.remove(filepath)
            print(f"[ELIMINADO] {filepath}")
        
        # Crear archivo nuevo
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[CREADO] {filepath}")
    
    print("\n" + "="*50)
    print("REPARACIÓN COMPLETADA")
    print("="*50)
    print("\nAhora recarga las páginas en tu navegador:")
    print("  - http://127.0.0.1:8000/admin-panel/dashboard/")
    print("  - http://127.0.0.1:8000/admin-panel/sales/")
    print("  - http://127.0.0.1:8000/admin-panel/signatures/")

if __name__ == '__main__':
    main()

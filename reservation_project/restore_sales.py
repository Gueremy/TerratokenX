
import os

content = r'''{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Ventas{% endblock %}
{% block page_title %}Gestión de Ventas{% endblock %}

{% block content %}
<div class="glass-panel rounded-2xl p-6 mb-6">
    <form method="get" class="flex flex-col md:flex-row gap-4 items-end">
        <div class="flex-1">
            <label class="block text-xs text-gray-500 uppercase mb-2">Estado de Pago</label>
            <select name="estado_pago" class="w-full bg-gray-800 border border-gray-700 rounded-xl p-3 text-white outline-none">
                <option value="">Todos</option>
                <option value="PENDIENTE" {% if request.GET.estado_pago == 'PENDIENTE' %}selected{% endif %}>Pendiente</option>
                <option value="EN_REVISION" {% if request.GET.estado_pago == 'EN_REVISION' %}selected{% endif %}>En Revisión</option>
                <option value="CONFIRMADO" {% if request.GET.estado_pago == 'CONFIRMADO' %}selected{% endif %}>Confirmado</option>
            </select>
        </div>
        <div class="flex gap-2">
            <a href="{% url 'admin_sales' %}" class="px-6 py-3 bg-gray-700 hover:bg-gray-600 text-white rounded-xl text-sm">Limpiar</a>
            <button type="submit" class="px-6 py-3 bg-blue-600 hover:bg-blue-700 text-white font-medium rounded-xl text-sm">Filtrar</button>
        </div>
    </form>
</div>

<div class="flex justify-between items-center mb-6">
    <div class="flex gap-3">
        <form method="post" action="{% url 'export_reservas_excel' %}">
            {% csrf_token %}
            <button type="submit" class="flex items-center gap-2 px-4 py-2 bg-green-600 hover:bg-green-700 text-white rounded-lg text-xs">
                <span class="material-icons text-sm">table_chart</span>Excel
            </button>
        </form>
        <form method="post" action="{% url 'export_reservas_pdf' %}">
            {% csrf_token %}
            <button type="submit" class="flex items-center gap-2 px-4 py-2 bg-red-600 hover:bg-red-700 text-white rounded-lg text-xs">
                <span class="material-icons text-sm">picture_as_pdf</span>PDF
            </button>
        </form>
    </div>
    <div class="text-gray-500 text-xs">
        Mostrando {{ reservas.count }} ventas
    </div>
</div>

<div class="glass-panel rounded-2xl overflow-hidden shadow-2xl">
    <div class="overflow-x-auto">
        <table class="w-full">
            <thead class="bg-gray-800/50">
                <tr class="text-left text-xs text-gray-400 uppercase">
                    <th class="px-6 py-4 font-bold">Cliente</th>
                    <th class="px-6 py-4 font-bold">Proyecto</th>
                    <th class="px-6 py-4 font-bold">Tokens</th>
                    <th class="px-6 py-4 font-bold">Total</th>
                    <th class="px-6 py-4 font-bold">Método</th>
                    <th class="px-6 py-4 font-bold">Estado</th>
                    <th class="px-6 py-4 font-bold">Acciones</th>
                </tr>
            </thead>
            <tbody class="divide-y divide-gray-800">
                {% for reserva in reservas %}
                <tr class="hover:bg-white/5 transition-colors">
                    <td class="px-6 py-4">
                        <p class="font-bold text-white">{{ reserva.nombre }}</p>
                        <p class="text-xs text-gray-500">{{ reserva.correo }}</p>
                    </td>
                    <td class="px-6 py-4 text-gray-300 text-sm">
                        {{ reserva.proyecto.nombre|default:"-" }}
                    </td>
                    <td class="px-6 py-4 text-white font-bold">{{ reserva.cantidad_tokens }}</td>
                    <td class="px-6 py-4 text-green-400 font-bold">${{ reserva.total|floatformat:0|intcomma }}</td>
                    <td class="px-6 py-4">
                        {% if reserva.metodo_pago == 'MP' %}
                        <span class="px-2 py-1 rounded bg-blue-500/10 text-blue-400 text-[10px] font-bold">Mercado Pago</span>
                        {% elif reserva.metodo_pago == 'CRYPTO' %}
                        <div class="flex flex-col">
                            <span class="px-2 py-1 rounded bg-orange-500/10 text-orange-400 text-[10px] font-bold">Crypto</span>
                            {% if reserva.crypto_currency %}<span class="text-[9px] text-yellow-500 mt-0.5">{{ reserva.crypto_currency }}</span>{% endif %}
                        </div>
                        {% elif reserva.metodo_pago == 'CRYPTO_MANUAL' %}
                        <div class="flex flex-col">
                            <span class="px-2 py-1 rounded bg-indigo-500/10 text-indigo-400 text-[10px] font-bold">Manual Cripto</span>
                            {% if reserva.crypto_currency %}<span class="text-[9px] text-yellow-500 mt-0.5">{{ reserva.crypto_currency }}</span>{% endif %}
                        </div>
                        {% else %}
                        <span class="px-2 py-1 rounded bg-gray-500/10 text-gray-400 text-[10px] font-bold">Manual</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4">
                        {% if reserva.estado_pago == 'CONFIRMADO' %}
                        <span class="px-2 py-1 rounded text-[10px] font-bold bg-green-500/10 text-green-400">Confirmado</span>
                        {% elif reserva.estado_pago == 'EN_REVISION' %}
                        <span class="px-2 py-1 rounded text-[10px] font-bold bg-yellow-500/10 text-yellow-400">En Revisión</span>
                        {% else %}
                        <span class="px-2 py-1 rounded text-[10px] font-bold bg-gray-500/10 text-gray-400">Pendiente</span>
                        {% endif %}
                    </td>
                    <td class="px-6 py-4 text-right">
                        <div class="flex items-center justify-end gap-2">
                            <a href="{% url 'editar_reserva' reserva.id %}" class="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:text-white transition-all">
                                <span class="material-icons text-sm">edit</span>
                            </a>
                        </div>
                    </td>
                </tr>
                {% empty %}
                <tr><td colspan="7" class="px-6 py-12 text-center text-gray-500">No hay ventas registradas.</td></tr>
                {% endfor %}
            </tbody>
        </table>
    </div>
</div>
{% endblock %}
'''

with open(r'booking\templates\booking\admin\sales.html', 'w', encoding='utf-8') as f:
    f.write(content)
    print("SUCCESS: sales.html restored.")
"

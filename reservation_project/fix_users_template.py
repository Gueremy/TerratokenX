
import os

content = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block content %}
<div class="space-y-6">

    <!-- Header -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h1 class="text-3xl font-bold text-white tracking-tight">Usuarios</h1>
            <p class="text-gray-400 mt-1">Gestión de inversores registrados en la plataforma</p>
        </div>

        <div class="bg-dark-800 border border-gold-500/20 rounded-lg px-4 py-2 flex items-center gap-3">
            <div class="w-2 h-2 rounded-full bg-green-500 animate-pulse"></div>
            <span class="text-gray-300 font-medium">Total: <span class="text-white font-bold">{{ total_usuarios }}</span></span>
        </div>
    </div>

    <!-- Tabla -->
    <div class="bg-dark-800 rounded-2xl border border-gold-500/10 overflow-hidden shadow-2xl">
        <div class="overflow-x-auto">
            <table class="w-full">
                <thead>
                    <tr class="bg-dark-900/50 border-b border-gray-700 text-left">
                        <th class="px-6 py-4 text-xs font-bold text-gold-500 uppercase tracking-wider">Usuario</th>
                        <th class="px-6 py-4 text-xs font-bold text-gold-500 uppercase tracking-wider">Tier</th>
                        <th class="px-6 py-4 text-xs font-bold text-gold-500 uppercase tracking-wider">Estado</th>
                        <th class="px-6 py-4 text-xs font-bold text-gold-500 uppercase tracking-wider text-right">
                            Acciones</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-700/50">
                    {% for usuario in usuarios %}
                    <tr class="hover:bg-white/5 transition-colors group">
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-3">
                                <div class="relative">
                                    <div
                                        class="w-10 h-10 rounded-full bg-gradient-to-br from-gold-500/20 to-gold-600/20 border border-gold-500/30 flex items-center justify-center text-gold-400 font-bold">
                                        {{ usuario.first_name|striptags|first|upper }}{{ usuario.last_name|striptags|first|upper }}
                                    </div>
                                    {% if usuario.profile.tier == 'Diamond' %}
                                    <div class="absolute -top-1 -right-1 bg-blue-500 rounded-full p-1 border border-dark-900"
                                        title="Diamond Member">
                                        <div class="w-2 h-2 bg-white rounded-full animate-pulse"></div>
                                    </div>
                                    {% endif %}
                                </div>
                                <div>
                                    <h4 class="font-bold text-white group-hover:text-gold-400 transition-colors">
                                        {{ usuario.first_name|striptags }} {{ usuario.last_name|striptags }}
                                        {% if not usuario.is_active %}
                                        <span
                                            class="ml-2 text-[10px] bg-red-500/20 text-red-500 px-2 py-0.5 rounded border border-red-500/20">BLOQUEADO</span>
                                        {% endif %}
                                    </h4>
                                    <div class="flex flex-col text-xs text-gray-500">
                                        <span>{{ usuario.email }}</span>
                                        <span class="opacity-50">ID: #{{ usuario.id }}</span>
                                    </div>
                                </div>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex flex-col gap-1">
                                <span class="text-sm font-medium text-white flex items-center gap-2">
                                    <i class="fas fa-crown text-gold-500 text-xs"></i>
                                    {{ usuario.profile.tier }}
                                </span>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex flex-col gap-2">
                                <!-- KYC Status -->
                                {% with profile=usuario.profile %}
                                {% if profile.kyc_status == 'APPROVED' %}
                                <span
                                    class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/10 text-green-400 border border-green-500/20 w-fit">
                                    KYC VERIFICADO
                                </span>
                                {% elif profile.kyc_status == 'PENDING' %}
                                <span
                                    class="px-2 py-0.5 rounded text-[10px] font-bold bg-yellow-500/10 text-yellow-400 border border-yellow-500/20 w-fit">
                                    KYC PENDIENTE
                                </span>
                                {% else %}
                                <span
                                    class="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-500/10 text-gray-400 border border-gray-500/20 w-fit">
                                    KYC NO INICIADO
                                </span>
                                {% endif %}

                                <!-- Wallet Status -->
                                {% if profile.wallet_address %}
                                <span class="text-[10px] text-gray-400 font-mono truncate max-w-[100px]"
                                    title="{{ profile.wallet_address }}">
                                    <i class="fas fa-wallet text-gray-600 mr-1"></i>{{ profile.wallet_address|slice:":6" }}...
                                </span>
                                {% endif %}
                                {% endwith %}
                            </div>
                        </td>
                        <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end gap-2">
                                <!-- Editar Usuario (Admin Django) -->
                                <a href="/admin/auth/user/{{ usuario.id }}/change/" target="_blank"
                                    class="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:bg-white hover:text-black transition-all"
                                    title="Editar Usuario">
                                    <span class="material-icons text-sm">edit</span>
                                </a>

                                <!-- Bloquear/Desbloquear -->
                                <form method="POST" action="{% url 'admin_user_toggle_active' usuario.id %}"
                                    class="inline">
                                    {% csrf_token %}
                                    <button type="submit"
                                        onclick="return confirm('¿Estás seguro de {% if usuario.is_active %}bloquear{% else %}desbloquear{% endif %} a este usuario?')"
                                        class="p-2 rounded-lg {% if usuario.is_active %}bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white{% else %}bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white{% endif %} transition-all"
                                        title="{% if usuario.is_active %}Bloquear Usuario{% else %}Desbloquear Usuario{% endif %}">
                                        <span class="material-icons text-sm">{% if usuario.is_active %}block{% else %}check_circle{% endif %}</span>
                                    </button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="4" class="px-6 py-12 text-center text-gray-500">
                            <span class="material-icons text-4xl mb-2 opacity-50">group_off</span>
                            <p>No hay usuarios registrados aún.</p>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>
<!-- Modal Change Tier -->
<div id="tierModal" class="fixed inset-0 z-50 hidden">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="closeModal('tierModal')"></div>
    <div
        class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-dark-900 border border-gold-500/30 rounded-xl p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-4">Cambiar Tier <span id="tierModalUser"
                class="text-gold-500"></span></h3>
        <form id="tierForm" method="POST" action="">
            {% csrf_token %}
            <div class="mb-4">
                <label class="block text-gray-400 text-sm mb-2">Nuevo Tier</label>
                <select name="tier"
                    class="w-full bg-black border border-gray-700 rounded p-2 text-white focus:border-gold-500 outline-none">
                    <option value="Standard">Standard</option>
                    <option value="Gold">Gold</option>
                    <option value="Platinum">Platinum</option>
                    <option value="Diamond">Diamond</option>
                </select>
            </div>
            <div class="flex justify-end gap-3">
                <button type="button" onclick="closeModal('tierModal')"
                    class="px-4 py-2 text-gray-400 hover:text-white">Cancelar</button>
                <button type="submit"
                    class="px-4 py-2 bg-gold-600 hover:bg-gold-500 text-black font-bold rounded">Guardar</button>
            </div>
        </form>
    </div>
</div>

<!-- Modal Credits -->
<div id="creditsModal" class="fixed inset-0 z-50 hidden">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="closeModal('creditsModal')"></div>
    <div
        class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-dark-900 border border-blue-500/30 rounded-xl p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-4">Ajustar Saldo <span id="creditsModalUser"
                class="text-blue-500"></span></h3>
        <form id="creditsForm" method="POST" action="">
            {% csrf_token %}
            <div class="mb-4">
                <label class="block text-gray-400 text-sm mb-2">Monto a Ajustar (USD)</label>
                <input type="number" step="0.01" name="monto"
                    class="w-full bg-black border border-gray-700 rounded p-2 text-white focus:border-blue-500 outline-none"
                    placeholder="+500 o -500">
                <p class="text-xs text-gray-500 mt-1">Usa valores negativos para restar saldo.</p>
            </div>
            <div class="mb-4">
                <label class="block text-gray-400 text-sm mb-2">Motivo</label>
                <input type="text" name="motivo"
                    class="w-full bg-black border border-gray-700 rounded p-2 text-white focus:border-blue-500 outline-none"
                    placeholder="Corrección administrativa..." required>
            </div>
            <div class="flex justify-end gap-3">
                <button type="button" onclick="closeModal('creditsModal')"
                    class="px-4 py-2 text-gray-400 hover:text-white">Cancelar</button>
                <button type="submit"
                    class="px-4 py-2 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded">Aplicar</button>
            </div>
        </form>
    </div>
</div>

<script>
    function closeModal(modalId) {
        document.getElementById(modalId).classList.add('hidden');
    }

    function openTierModal(url, username, currentTier) {
        document.getElementById('tierModal').classList.remove('hidden');
        document.getElementById('tierModalUser').textContent = username;

        // Update Action URL
        const form = document.getElementById('tierForm');
        form.action = url;

        // Set Current Value
        const select = form.querySelector('select[name="tier"]');
        if (select) select.value = currentTier;
    }

    function openCreditsModal(url, username) {
        document.getElementById('creditsModal').classList.remove('hidden');
        document.getElementById('creditsModalUser').textContent = username;

        // Update Action URL
        const form = document.getElementById('creditsForm');
        form.action = url;
    }
</script>
{% endblock %}
"""

file_path = os.path.join(os.getcwd(), 'booking', 'templates', 'booking', 'admin', 'users.html')

try:
    with open(file_path, 'w', encoding='utf-8') as f:
        f.write(content)
    print(f"File rewritten successfully to {file_path}")
except Exception as e:
    print(f"Error writing file: {e}")

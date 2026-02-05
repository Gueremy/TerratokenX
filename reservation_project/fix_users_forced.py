
import os

content = r'''{% extends 'booking/admin/base_admin.html' %}
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
                        <th class="px-6 py-4 text-xs font-bold text-gold-500 uppercase tracking-wider text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-700/50">
                    {% for usuario in usuarios %}
                    <tr class="hover:bg-white/5 transition-colors group">
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-3">
                                <div class="relative">
                                    <div class="w-10 h-10 rounded-full bg-gradient-to-br from-gold-500/20 to-gold-600/20 border border-gold-500/30 flex items-center justify-center text-gold-400 font-bold">
                                        {{ usuario.first_name|slice:":1"|upper }}{{ usuario.last_name|slice:":1"|upper }}
                                    </div>
                                    {% if usuario.is_staff %}
                                    <div class="absolute -top-1 -right-1 bg-blue-500 rounded-full p-1 border border-dark-900" title="Staff">
                                        <div class="w-1 h-1 bg-white rounded-full"></div>
                                    </div>
                                    {% endif %}
                                </div>
                                <div>
                                    <h4 class="font-bold text-white group-hover:text-gold-400 transition-colors">
                                        {{ usuario.first_name }} {{ usuario.last_name }}
                                        {% if not usuario.is_active %}
                                        <span class="ml-2 text-[10px] bg-red-500/20 text-red-500 px-2 py-0.5 rounded border border-red-500/20">BLOQUEADO</span>
                                        {% endif %}
                                    </h4>
                                    <div class="flex flex-col text-xs text-gray-500">
                                        <span>{{ usuario.email }}</span>
                                        <span class="opacity-50">ID: #{{ usuario.id }}</span>
                                    </div>
                                </div>
                            </div>
                        </td>
                        <td class="px-6 py-4 font-bold text-gray-400">
                            {% if usuario.is_staff %}
                                <span class="text-gold-500">ADMIN</span>
                            {% else %}
                                BRONZE
                            {% endif %}
                        </td>
                        <td class="px-6 py-4">
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-gray-500/10 text-gray-400 border border-gray-500/20 w-fit">
                                KYC NO INICIADO
                            </span>
                        </td>
                        <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end gap-2">
                                <!-- Editar -->
                                <button type="button" 
                                        onclick="openEditModal('{{ usuario.id }}', '{{ usuario.first_name }}', '{{ usuario.last_name }}', '{{ usuario.email }}')"
                                        class="p-2 rounded-lg bg-gray-700/50 text-gray-400 hover:bg-white hover:text-black transition-all">
                                    <span class="material-icons text-sm">edit</span>
                                </button>
                                <!-- Bloquear -->
                                <form method="POST" action="{% url 'admin_block_user' usuario.id %}" class="inline">
                                    {% csrf_token %}
                                    <button type="submit" class="p-2 rounded-lg {% if usuario.is_active %}bg-red-500/10 text-red-500 hover:bg-red-500 hover:text-white{% else %}bg-green-500/10 text-green-500 hover:bg-green-500 hover:text-white{% endif %} transition-all">
                                        <span class="material-icons text-sm">{% if usuario.is_active %}block{% else %}check_circle{% endif %}</span>
                                    </button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="4" class="px-6 py-12 text-center text-gray-500">No hay usuarios.</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Modal -->
<div id="editUserModal" class="fixed inset-0 z-50 hidden">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="closeEditModal()"></div>
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-dark-900 border border-gold-500/30 rounded-xl p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-4">Editar Usuario</h3>
        <form id="editUserForm" method="POST" action="">
            {% csrf_token %}
            <div class="space-y-4">
                <div>
                    <label class="block text-gray-400 text-sm mb-2">Nombre</label>
                    <input type="text" name="first_name" id="edit_first_name" required class="w-full bg-black border border-gray-700 rounded p-2 text-white outline-none">
                </div>
                <div>
                    <label class="block text-gray-400 text-sm mb-2">Apellido</label>
                    <input type="text" name="last_name" id="edit_last_name" required class="w-full bg-black border border-gray-700 rounded p-2 text-white outline-none">
                </div>
                <div>
                    <label class="block text-gray-400 text-sm mb-2">Email</label>
                    <input type="email" name="email" id="edit_email" required class="w-full bg-black border border-gray-700 rounded p-2 text-white outline-none">
                </div>
            </div>
            <div class="flex justify-end gap-3 mt-6">
                <button type="button" onclick="closeEditModal()" class="px-4 py-2 text-gray-400">Cancelar</button>
                <button type="submit" class="px-4 py-2 bg-gold-600 text-black font-bold rounded">Guardar</button>
            </div>
        </form>
    </div>
</div>

<script>
    function openEditModal(id, f, l, e) {
        document.getElementById('editUserModal').classList.remove('hidden');
        document.getElementById('edit_first_name').value = f;
        document.getElementById('edit_last_name').value = l;
        document.getElementById('edit_email').value = e;
        document.getElementById('editUserForm').action = "/admin-panel/users/edit/" + id + "/";
    }
    function closeEditModal() {
        document.getElementById('editUserModal').classList.add('hidden');
    }
</script>
{% endblock %}
'''

with open(r'booking\templates\booking\admin\users.html', 'w', encoding='utf-8') as f:
    f.write(content)
    print("SUCCESS: Users template fixed via Python forced write.")

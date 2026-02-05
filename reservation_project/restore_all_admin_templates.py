import os

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
TEMPLATE_DIR = os.path.join(BASE_DIR, 'booking', 'templates', 'booking', 'admin')

# 1. PROJECTS TEMPLATE
PROJECTS_CONTENT = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Proyectos{% endblock %}
{% block page_title %}Gestión de Proyectos{% endblock %}

{% block content %}
<div class="space-y-6">
    <!-- Header Actions -->
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h1 class="text-3xl font-bold text-white tracking-tight">Proyectos</h1>
            <p class="text-gray-400 mt-1">Administra el catálogo de tokens inmobiliarios</p>
        </div>
        <a href="{% url 'project_create' %}" class="px-6 py-3 bg-gold-600 hover:bg-gold-500 text-black font-bold rounded-xl shadow-lg flex items-center gap-2 transition-all">
            <span class="material-icons">add_circle</span>
            Nuevo Proyecto
        </a>
    </div>

    <!-- Lista de Proyectos -->
    <div class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
        {% for proyecto in proyectos %}
        <div class="glass-panel rounded-2xl overflow-hidden border border-gold-500/10 hover:border-gold-500/30 transition-all flex flex-col group">
            <div class="relative h-48 overflow-hidden">
                {% if proyecto.imagen_portada_url %}
                    <img src="{{ proyecto.imagen_portada_url }}" alt="{{ proyecto.nombre }}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500">
                {% elif proyecto.imagen_portada %}
                    <img src="{{ proyecto.imagen_portada.url }}" alt="{{ proyecto.nombre }}" class="w-full h-full object-cover group-hover:scale-110 transition-transform duration-500">
                {% else %}
                    <div class="w-full h-full bg-dark-700 flex items-center justify-center text-gray-600">
                        <span class="material-icons text-5xl">image_not_supported</span>
                    </div>
                {% endif %}
                
                <div class="absolute top-4 right-4 flex gap-2">
                    {% if proyecto.activo %}
                        <span class="px-2 py-1 rounded bg-green-500/80 text-white text-[10px] font-bold">ACTIVO</span>
                    {% else %}
                        <span class="px-2 py-1 rounded bg-red-500/80 text-white text-[10px] font-bold">OCULTO</span>
                    {% endif %}
                    <span class="px-2 py-1 rounded bg-blue-500/80 text-white text-[10px] font-bold">{{ proyecto.tipo|upper }}</span>
                </div>
            </div>
            
            <div class="p-6 flex-1 flex flex-col">
                <div class="mb-4">
                    <h3 class="text-xl font-bold text-white mb-1 group-hover:text-gold-400 transition-colors">{{ proyecto.nombre }}</h3>
                    <p class="text-xs text-gray-500 flex items-center gap-1">
                        <span class="material-icons text-xs">location_on</span>
                        {{ proyecto.ubicacion }}
                    </p>
                </div>
                
                <div class="grid grid-cols-2 gap-4 mb-6 text-sm">
                    <div>
                        <p class="text-gray-500 text-xs">Precio Token</p>
                        <p class="text-white font-bold text-lg">${{ proyecto.precio_token|intcomma }}</p>
                    </div>
                    <div>
                        <p class="text-gray-500 text-xs">Retorno Est.</p>
                        <p class="text-gold-500 font-bold text-lg">{{ proyecto.rentabilidad_estimada }}</p>
                    </div>
                </div>
                
                <div class="mt-auto flex items-center gap-2">
                    <a href="{% url 'project_edit' proyecto.id %}" class="flex-1 bg-white/5 hover:bg-white/10 text-white font-medium py-2 rounded-lg text-center text-sm border border-white/10 transition-colors flex items-center justify-center gap-1">
                        <span class="material-icons text-sm">edit</span> Editar
                    </a>
                    <a href="{% url 'project_delete' proyecto.id %}" onclick="return confirm('¿Seguro?')" class="w-10 h-10 bg-red-500/10 hover:bg-red-500/20 text-red-500 rounded-lg flex items-center justify-center border border-red-500/20 transition-colors">
                        <span class="material-icons text-lg">delete</span>
                    </a>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-span-full py-20 text-center glass-panel rounded-2xl border-2 border-dashed border-gray-700">
            <span class="material-icons text-5xl text-gray-600 mb-4">apartment</span>
            <p class="text-gray-400 font-medium">No hay proyectos registrados aún.</p>
            <a href="{% url 'project_create' %}" class="mt-4 inline-block text-gold-500 hover:text-gold-400 font-bold underline">Crea el primer proyecto</a>
        </div>
        {% endfor %}
    </div>
</div>
{% endblock %}
"""

# 2. COUPONS TEMPLATE
COUPONS_CONTENT = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Cupones{% endblock %}
{% block page_title %}Marketing & Cupones{% endblock %}

{% block content %}
<div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h1 class="text-3xl font-bold text-white tracking-tight">Cupones de Descuento</h1>
            <p class="text-gray-400 mt-1">Campañas promocionales e incentivos</p>
        </div>
        <button onclick="document.getElementById('couponModal').classList.remove('hidden')" class="px-6 py-3 bg-blue-600 hover:bg-blue-500 text-white font-bold rounded-xl shadow-lg flex items-center gap-2 transition-all">
            <span class="material-icons">add_circle</span>
            Nuevo Cupón
        </button>
    </div>

    <div class="glass-panel rounded-2xl overflow-hidden shadow-2xl">
        <div class="overflow-x-auto">
            <table class="w-full">
                <thead>
                    <tr class="bg-dark-900/50 border-b border-gray-700 text-left">
                        <th class="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Código</th>
                        <th class="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Descuento</th>
                        <th class="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Validez</th>
                        <th class="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider">Estado</th>
                        <th class="px-6 py-4 text-xs font-bold text-gray-400 uppercase tracking-wider text-right">Acciones</th>
                    </tr>
                </thead>
                <tbody class="divide-y divide-gray-700/50">
                    {% for coupon in coupons %}
                    <tr class="hover:bg-white/5 transition-colors">
                        <td class="px-6 py-4">
                            <span class="font-mono font-bold text-white text-lg bg-dark-900 px-3 py-1 rounded border border-gray-700">{{ coupon.code }}</span>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex items-center gap-2">
                                <span class="text-green-400 font-bold text-xl">{{ coupon.discount_percentage }}%</span>
                                <span class="text-xs text-gray-500 uppercase">OFF</span>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            <div class="flex flex-col text-xs text-gray-400">
                                <span>Desde: {{ coupon.valid_from|date:"d M Y" }}</span>
                                <span>Hasta: {{ coupon.valid_to|date:"d M Y" }}</span>
                            </div>
                        </td>
                        <td class="px-6 py-4">
                            {% if coupon.is_valid %}
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-green-500/10 text-green-400 border border-green-500/20">ACTIVO</span>
                            {% else %}
                            <span class="px-2 py-0.5 rounded text-[10px] font-bold bg-red-500/10 text-red-400 border border-red-500/20">EXPIRADO</span>
                            {% endif %}
                        </td>
                        <td class="px-6 py-4 text-right">
                            <div class="flex items-center justify-end gap-2">
                                <form method="post" action="{% url 'admin_coupon_delete' coupon.id %}" onsubmit="return confirm('¿Eliminar cupón?')">
                                    {% csrf_token %}
                                    <button type="submit" class="p-2 text-red-400 hover:bg-red-500/10 rounded-lg transition-all">
                                        <span class="material-icons text-lg">delete</span>
                                    </button>
                                </form>
                            </div>
                        </td>
                    </tr>
                    {% empty %}
                    <tr>
                        <td colspan="5" class="px-6 py-20 text-center text-gray-500">
                            <span class="material-icons text-5xl mb-4 opacity-30">loyalty</span>
                            <p>No hay cupones activos.</p>
                        </td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        </div>
    </div>
</div>

<!-- Modal Cupón -->
<div id="couponModal" class="fixed inset-0 z-50 hidden">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="this.parentElement.classList.add('hidden')"></div>
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-dark-900 border border-gold-500/30 rounded-xl p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-6">Crear Nuevo Cupón</h3>
        <form method="POST" action="{% url 'admin_coupon_create' %}" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="block text-gray-400 text-xs font-bold uppercase mb-2">Código del Cupón</label>
                <input type="text" name="code" required class="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:border-gold-500 outline-none uppercase font-mono" placeholder="EJ: BIENVENIDA10">
            </div>
            <div>
                <label class="block text-gray-400 text-xs font-bold uppercase mb-2">Porcentaje de Descuento (%)</label>
                <input type="number" name="discount_percentage" required class="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:border-gold-500 outline-none" min="1" max="100">
            </div>
            <div class="grid grid-cols-2 gap-4">
                <div>
                    <label class="block text-gray-400 text-xs font-bold uppercase mb-2">Válido desde</label>
                    <input type="date" name="valid_from" required class="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:border-gold-500 outline-none text-sm">
                </div>
                <div>
                    <label class="block text-gray-400 text-xs font-bold uppercase mb-2">Válido hasta</label>
                    <input type="date" name="valid_to" required class="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:border-gold-500 outline-none text-sm">
                </div>
            </div>
            <div class="flex justify-end gap-3 mt-8">
                <button type="button" onclick="this.closest('#couponModal').classList.add('hidden')" class="px-4 py-2 text-gray-400 hover:text-white">Cancelar</button>
                <button type="submit" class="px-6 py-2 bg-gold-600 hover:bg-gold-500 text-black font-bold rounded-lg shadow-lg transition-all">Crear Cupón</button>
            </div>
        </form>
    </div>
</div>
{% endblock %}
"""

# 3. KYC TEMPLATE
KYC_CONTENT = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}KYC Compliance{% endblock %}
{% block page_title %}Verificación de Identidad{% endblock %}

{% block content %}
<div class="space-y-6">
    <div class="flex flex-col md:flex-row md:items-center justify-between gap-4">
        <div>
            <h1 class="text-3xl font-bold text-white tracking-tight text-gold-gradient">KYC | Compliance</h1>
            <p class="text-gray-400 mt-1">Revisión de identidad y origen de fondos</p>
        </div>
        
        <div class="bg-dark-800 border border-gold-500/20 rounded-lg px-4 py-2 flex items-center gap-3">
            <span class="text-gray-400 font-medium">Revisiones pendientes: <span class="text-gold-500 font-bold">{{ kyc_applications.count }}</span></span>
        </div>
    </div>

    <div class="grid grid-cols-1 gap-6">
        {% for app in kyc_applications %}
        <div class="glass-panel rounded-2xl p-6 border border-gold-500/10 hover:border-gold-500/20 transition-all">
            <div class="flex flex-col lg:flex-row gap-8">
                <!-- Data -->
                <div class="lg:w-1/3">
                    <div class="flex items-center gap-4 mb-6">
                        <div class="w-14 h-14 rounded-full bg-gradient-to-br from-gold-500 to-gold-600 flex items-center justify-center text-dark-900 font-bold text-xl">
                            {{ app.user.first_name|first|upper }}{{ app.user.last_name|first|upper }}
                        </div>
                        <div>
                            <h3 class="text-xl font-bold text-white">{{ app.user.first_name }} {{ app.user.last_name }}</h3>
                            <p class="text-sm text-gray-500">ID Usuario: #{{ app.user.id }}</p>
                            <span class="text-[10px] bg-gold-500/20 text-gold-500 px-2 py-0.5 rounded border border-gold-500/20">Nivel Solicitado: V{{ app.nivel_solicitado }}</span>
                        </div>
                    </div>
                    
                    <div class="space-y-4">
                        <div class="p-4 bg-dark-900 rounded-xl border border-gray-700">
                            <p class="text-[10px] text-gray-500 uppercase font-bold mb-2">Declaración Origen de Fondos</p>
                            <p class="text-sm text-gray-300 italic">"{{ app.origen_fondos|default:"No declarada" }}"</p>
                        </div>
                        <p class="text-xs text-gray-500">Enviado: {{ app.created_at|date:"d M Y H:i" }}</p>
                        
                        <div class="flex gap-2">
                            <form method="POST" action="{% url 'admin_kyc_approve' app.id %}" class="flex-1">
                                {% csrf_token %}
                                <button type="submit" class="w-full bg-green-600 hover:bg-green-500 text-white font-bold py-2 rounded-lg text-sm transition-all flex items-center justify-center gap-1">
                                    <span class="material-icons text-sm">verified</span> Aprobar
                                </button>
                            </form>
                            <button onclick="openRejectModal('{{ app.id }}')" class="flex-1 bg-red-600/20 hover:bg-red-600/40 text-red-500 font-bold py-2 rounded-lg text-sm transition-all border border-red-500/30">
                                Rechazar
                            </button>
                        </div>
                    </div>
                </div>
                
                <!-- Photos -->
                <div class="lg:w-2/3 grid grid-cols-1 md:grid-cols-3 gap-4">
                    <div class="space-y-2">
                        <p class="text-[10px] text-gray-500 uppercase font-bold text-center">Frente DNI</p>
                        <a href="{{ app.documento_frente.url }}" target="_blank" class="block h-48 rounded-xl overflow-hidden border border-gray-700 hover:border-gold-500/50 transition-all">
                            <img src="{{ app.documento_frente.url }}" class="w-full h-full object-cover">
                        </a>
                    </div>
                    <div class="space-y-2">
                        <p class="text-[10px] text-gray-500 uppercase font-bold text-center">Reverso DNI</p>
                        {% if app.documento_reverso %}
                        <a href="{{ app.documento_reverso.url }}" target="_blank" class="block h-48 rounded-xl overflow-hidden border border-gray-700 hover:border-gold-500/50 transition-all">
                            <img src="{{ app.documento_reverso.url }}" class="w-full h-full object-cover">
                        </a>
                        {% else %}
                        <div class="h-48 rounded-xl bg-dark-900 border border-dashed border-gray-700 flex items-center justify-center text-gray-600">
                             <span class="text-xs italic">No aplica</span>
                        </div>
                        {% endif %}
                    </div>
                    <div class="space-y-2">
                        <p class="text-[10px] text-gray-500 uppercase font-bold text-center">Selfie Verificación</p>
                        <a href="{{ app.selfie.url }}" target="_blank" class="block h-48 rounded-xl overflow-hidden border border-gray-700 hover:border-gold-500/50 transition-all">
                            <img src="{{ app.selfie.url }}" class="w-full h-full object-cover">
                        </a>
                    </div>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="py-20 text-center glass-panel rounded-2xl border-2 border-dashed border-gray-700 col-span-full">
            <span class="material-icons text-5xl text-gray-600 mb-4">fingerprint</span>
            <p class="text-gray-400 font-medium">No hay solicitudes de validación pendientes.</p>
        </div>
        {% endfor %}
    </div>
</div>

<!-- Modal Rechazo -->
<div id="rejectModal" class="fixed inset-0 z-50 hidden">
    <div class="absolute inset-0 bg-black/80 backdrop-blur-sm" onclick="this.parentElement.classList.add('hidden')"></div>
    <div class="absolute top-1/2 left-1/2 transform -translate-x-1/2 -translate-y-1/2 w-full max-w-md bg-dark-900 border border-red-500/30 rounded-xl p-6 shadow-2xl">
        <h3 class="text-xl font-bold text-white mb-6">Rechazar Solicitud</h3>
        <form id="rejectForm" method="POST" action="" class="space-y-4">
            {% csrf_token %}
            <div>
                <label class="block text-gray-400 text-xs font-bold uppercase mb-2">Motivo del Rechazo</label>
                <textarea name="admin_notes" required class="w-full bg-black border border-gray-700 rounded-lg p-3 text-white focus:border-red-500 outline-none h-32" placeholder="Ej: La foto no se ve clara..."></textarea>
            </div>
            <div class="flex justify-end gap-3 mt-8">
                <button type="button" onclick="document.getElementById('rejectModal').classList.add('hidden')" class="px-4 py-2 text-gray-400 hover:text-white">Cancelar</button>
                <button type="submit" class="px-6 py-2 bg-red-600 hover:bg-red-500 text-white font-bold rounded-lg shadow-lg transition-all">Confirmar Rechazo</button>
            </div>
        </form>
    </div>
</div>

<script>
function openRejectModal(id) {
    const modal = document.getElementById('rejectModal');
    const form = document.getElementById('rejectForm');
    form.action = `/admin-panel/kyc/${id}/reject/`;
    modal.classList.remove('hidden');
}
</script>
{% endblock %}
"""

def main():
    files = {
        'projects.html': PROJECTS_CONTENT,
        'coupons.html': COUPONS_CONTENT,
        'kyc.html': KYC_CONTENT,
    }
    
    for filename, content in files.items():
        filepath = os.path.join(TEMPLATE_DIR, filename)
        with open(filepath, 'w', encoding='utf-8') as f:
            f.write(content)
        print(f"[RECOVERED] {filepath}")

if __name__ == '__main__':
    main()

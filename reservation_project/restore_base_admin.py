
import os

content = r"""{% load static %}
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>TerraToken ERP | {% block title %}Dashboard{% endblock %}</title>
    <script src="https://cdn.tailwindcss.com"></script>
    <link href="https://fonts.googleapis.com/icon?family=Material+Icons" rel="stylesheet">
    <link href="https://fonts.googleapis.com/css2?family=Inter:wght@300;400;500;600;700&display=swap" rel="stylesheet">
    <script src="https://cdn.jsdelivr.net/npm/chart.js"></script>
    <script>
        tailwind.config = {
            theme: {
                extend: {
                    colors: {
                        gold: {
                            50: '#fff9e6', 100: '#fef0c3', 200: '#fde68a', 300: '#fcd34d', 400: '#f4c430',
                            500: '#d4af37', 600: '#b8960f', 700: '#92750c', 800: '#6b5610', 900: '#4a3c12',
                        },
                        dark: {
                            900: '#0a0a0a', 800: '#111111', 700: '#1a1a1a', 600: '#242424', 500: '#2d2d2d',
                        }
                    }
                }
            }
        }
    </script>
    <style>
        body { font-family: 'Inter', sans-serif; background: #0a0a0a; color: #f3f4f6; }
        .glass-panel { background: rgba(17, 17, 17, 0.8); backdrop-filter: blur(10px); border: 1px solid rgba(212, 175, 55, 0.1); }
        .nav-item.active { background: rgba(212, 175, 55, 0.1); border-left: 3px solid #d4af37; color: #d4af37; }
        .nav-item:hover { background: rgba(255, 255, 255, 0.05); }
        .custom-scrollbar::-webkit-scrollbar { width: 4px; }
        .custom-scrollbar::-webkit-scrollbar-track { background: #0a0a0a; }
        .custom-scrollbar::-webkit-scrollbar-thumb { background: #d4af37; border-radius: 10px; }
    </style>
</head>
<body class="bg-dark-900 h-screen flex overflow-hidden">

    <!-- Sidebar -->
    <aside class="w-64 bg-dark-800 border-r border-gold-500/10 flex flex-col hidden md:flex">
        <div class="p-6 border-b border-gold-500/10 flex items-center gap-3">
            <div class="w-10 h-10 bg-gold-500 rounded-lg flex items-center justify-center font-bold text-dark-900 shadow-lg">T</div>
            <span class="text-xl font-bold text-white">TerraToken<span class="text-gold-500">X</span></span>
        </div>

        <nav class="flex-1 overflow-y-auto py-6 px-3 space-y-1 custom-scrollbar">
            <p class="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2">Menú</p>
            
            <a href="{% url 'admin_dashboard' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'dashboard' or menu_active == 'dashboard' %}active{% endif %}">
                <span class="material-icons text-xl">dashboard</span>
                <span class="text-sm font-medium">Resumen</span>
            </a>

            <a href="{% url 'admin_sales' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'sales' or menu_active == 'sales' %}active{% endif %}">
                <span class="material-icons text-xl">payments</span>
                <span class="text-sm font-medium">Compras</span>
                {% if pending_count > 0 %}
                <span class="ml-auto bg-gold-500 text-black py-0.5 px-2 rounded-full text-[10px] font-bold">{{ pending_count }}</span>
                {% endif %}
            </a>

            <a href="{% url 'admin_projects' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'projects' or menu_active == 'projects' %}active{% endif %}">
                <span class="material-icons text-xl">apartment</span>
                <span class="text-sm font-medium">Proyectos</span>
            </a>

            <a href="{% url 'admin_coupons' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'coupons' or menu_active == 'coupons' %}active{% endif %}">
                <span class="material-icons text-xl">loyalty</span>
                <span class="text-sm font-medium">Cupones</span>
            </a>

            <a href="{% url 'admin_users' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'users' or menu_active == 'users' %}active{% endif %}">
                <span class="material-icons text-xl">people</span>
                <span class="text-sm font-medium">Usuarios</span>
            </a>

            <p class="px-3 text-xs font-semibold text-gray-500 uppercase tracking-wider mb-2 mt-6">Sistema</p>
            <a href="{% url 'admin_signatures' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400 {% if active_tab == 'signatures' or menu_active == 'signatures' %}active{% endif %}">
                <span class="material-icons text-xl">verified_user</span>
                <span class="text-sm font-medium">Firmas</span>
            </a>
            <a href="{% url 'admin_panel' %}" class="nav-item flex items-center gap-3 px-3 py-3 rounded-lg text-gray-400">
                <span class="material-icons text-xl">settings</span>
                <span class="text-sm font-medium">Configuración</span>
            </a>
        </nav>

        <div class="p-4 border-t border-gold-500/10">
            <div class="flex items-center gap-3 mb-4 px-2">
                <div class="w-8 h-8 rounded-full bg-gold-500/20 flex items-center justify-center text-gold-500 text-xs font-bold">{{ request.user.username|slice:":1"|upper }}</div>
                <div class="flex-1 min-w-0">
                    <p class="text-sm font-bold text-white truncate">{{ request.user.first_name|default:request.user.username }}</p>
                    <p class="text-[10px] text-gray-500 truncate">Administrador</p>
                </div>
            </div>
            <a href="{% url 'logout' %}" class="flex items-center gap-3 px-3 py-2 rounded-lg text-red-400 hover:bg-red-400/10 transition-colors">
                <span class="material-icons text-xl">logout</span>
                <span class="text-sm font-medium">Cerrar Sesión</span>
            </a>
        </div>
    </aside>

    <!-- Main Content -->
    <main class="flex-1 flex flex-col min-w-0 overflow-hidden relative">
        <!-- Top Bar -->
        <header class="h-16 border-b border-gold-500/10 flex items-center justify-between px-8 bg-dark-800/50 backdrop-blur-md z-10">
            <h2 class="text-lg font-bold text-white">{% block page_title %}Dashboard{% endblock %}</h2>
            <div class="flex items-center gap-4 text-xs text-gray-500">
                <span>Versión 2.0.1</span>
            </div>
        </header>

        <!-- Content Area -->
        <div class="flex-1 overflow-y-auto p-8 custom-scrollbar relative">
            {% if messages %}
            <div class="fixed top-4 right-4 z-50 space-y-2 max-w-sm">
                {% for message in messages %}
                <div class="p-4 rounded-lg border flex justify-between items-center gap-4 bg-dark-800 shadow-2xl transition-all border-gold-500/30">
                    <span class="text-sm text-gray-100">{{ message }}</span>
                    <button onclick="this.parentElement.remove()" class="text-xs text-gray-500 hover:text-white">✕</button>
                </div>
                {% endfor %}
            </div>
            {% endif %}

            {% block content %}{% endblock %}
        </div>
    </main>
</body>
</html>
"""

with open(r'booking\templates\booking\admin\base_admin.html', 'w', encoding='utf-8') as f:
    f.write(content)
"""

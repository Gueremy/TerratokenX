import os

BASE_DIR = os.getcwd()
TEMPLATE_DIR = os.path.join(BASE_DIR, 'booking', 'templates', 'booking')
ADMIN_TEMPLATE_DIR = os.path.join(TEMPLATE_DIR, 'admin')

# --- 1. RESERVATION FORM (FRONTEND) ---
RESERVATION_FORM_CONTENT = """{% extends 'booking/base.html' %}
{% load static %}

{% block content %}
<div class="row justify-content-center">
    <div class="col-lg-10">
        <div class="card shadow-lg border-0 rounded-4 overflow-hidden mb-5">
            <div class="row g-0">
                <!-- Sidebar Info -->
                <div class="col-md-4 bg-black p-5 text-white d-flex flex-column justify-content-center border-end border-secondary">
                    <div class="mb-4">
                        <img src="{% static 'booking/img/Terratoken_logo-removebg-preview2.png' %}" alt="Logo" class="img-fluid mb-4" style="max-height: 80px;">
                        <h2 class="display-6 fw-bold text-gold">Invierte en Real Estate</h2>
                        <p class="text-muted">Adquiere tokens respaldados por activos reales en la Patagonia Chilena con total seguridad y transparencia.</p>
                    </div>
                    
                    <div class="mt-4">
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-check-circle text-gold me-3"></i>
                            <span>Respaldo en Activos Reales</span>
                        </div>
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-check-circle text-gold me-3"></i>
                            <span>Retorno estimado 12-18%</span>
                        </div>
                        <div class="d-flex align-items-center mb-3">
                            <i class="fas fa-check-circle text-gold me-3"></i>
                            <span>Liquidez Digital</span>
                        </div>
                    </div>
                </div>

                <!-- Form Area -->
                <div class="col-md-8 p-5 bg-dark">
                    <h3 class="fw-bold text-white mb-4">Formulario de Inversión</h3>
                    
                    <form method="post" id="reservationForm" class="needs-validation" novalidate>
                        {% csrf_token %}
                        
                        <!-- Selección de Proyecto -->
                        <div class="mb-4">
                            <label class="form-label text-muted small fw-bold text-uppercase">1. Selecciona el Proyecto</label>
                            <select name="proyecto" id="id_proyecto" class="form-select form-select-lg bg-black text-white border-secondary" required>
                                <option value="" selected disabled>Elige un proyecto...</option>
                                {% for proyecto in proyectos %}
                                <option value="{{ proyecto.id }}" data-price="{{ proyecto.precio_token }}">
                                    {{ proyecto.nombre }} - ${{ proyecto.precio_token }}/token
                                </option>
                                {% endfor %}
                            </select>
                        </div>

                        <!-- Cantidad de Tokens -->
                        <div class="mb-4">
                            <label class="form-label text-muted small fw-bold text-uppercase">2. Cantidad de Tokens</label>
                            <div class="input-group input-group-lg">
                                <button type="button" class="btn btn-outline-secondary border-secondary" onclick="updateQty(-1)">-</button>
                                <input type="number" name="cantidad_tokens" id="id_cantidad_tokens" value="1" min="1" class="form-control bg-black text-white border-secondary text-center fw-bold" required>
                                <button type="button" class="btn btn-outline-secondary border-secondary" onclick="updateQty(1)">+</button>
                            </div>
                        </div>

                        <!-- Datos Personales -->
                        <div class="mb-4">
                            <label class="form-label text-muted small fw-bold text-uppercase">3. Datos del Inversor</label>
                            <div class="row g-3">
                                <div class="col-md-6">
                                    <input type="text" name="nombre" placeholder="Nombre Completo" class="form-control bg-black text-white border-secondary" required>
                                </div>
                                <div class="col-md-6">
                                    <input type="email" name="correo" placeholder="Email Contacto" class="form-control bg-black text-white border-secondary" required>
                                </div>
                                <div class="col-md-6">
                                    <input type="text" name="telefono" placeholder="Teléfono" class="form-control bg-black text-white border-secondary" required>
                                </div>
                                <div class="col-md-6">
                                    <input type="text" name="rut" placeholder="RUT / ID Tax" class="form-control bg-black text-white border-secondary" required>
                                </div>
                                <div class="col-12">
                                    <input type="text" name="direccion" placeholder="Dirección de Domicilio" class="form-control bg-black text-white border-secondary" required>
                                </div>
                            </div>
                        </div>

                        <!-- Cupón de Descuento -->
                        <div class="mb-4">
                            <label class="form-label text-muted small fw-bold text-uppercase">4. Cupón de Descuento</label>
                            <div class="input-group">
                                <input type="text" id="coupon_code" class="form-control bg-black text-white border-secondary text-uppercase" placeholder="Código Promocional">
                                <button type="button" class="btn btn-outline-gold" onclick="applyCoupon()">Aplicar</button>
                            </div>
                            <div id="coupon_msg" class="mt-2 small"></div>
                            <input type="hidden" name="coupon" id="id_coupon">
                        </div>

                        <!-- Método de Pago -->
                        <div class="mb-4">
                            <label class="form-label text-muted small fw-bold text-uppercase">5. Método de Pago</label>
                            <div class="row g-2">
                                <div class="col-md-6">
                                    <input type="radio" name="metodo_pago" value="MP" id="pay_mp" class="btn-check" checked required>
                                    <label class="btn btn-outline-primary w-100 py-3 d-flex align-items-center justify-content-center" for="pay_mp">
                                        <i class="fas fa-credit-card me-2"></i> Mercado Pago
                                    </label>
                                </div>
                                <div class="col-md-6">
                                    <input type="radio" name="metodo_pago" value="CRYPTO" id="pay_crypto" class="btn-check" required>
                                    <label class="btn btn-outline-warning w-100 py-3 d-flex align-items-center justify-content-center" for="pay_crypto">
                                        <i class="fab fa-bitcoin me-2"></i> Crypto (Manual)
                                    </label>
                                </div>
                            </div>
                        </div>

                        <!-- Total Resume -->
                        <div class="p-4 bg-black rounded-3 mb-4 border border-secondary shadow-sm">
                            <div class="d-flex justify-content-between mb-2">
                                <span class="text-muted">Subtotal</span>
                                <span class="text-white" id="subtotal_display">$0</span>
                            </div>
                            <div class="d-flex justify-content-between mb-2 text-gold d-none" id="discount_row">
                                <span>Descuento (<span id="discount_pct">0</span>%)</span>
                                <span id="discount_display">-$0</span>
                            </div>
                            <hr class="border-secondary">
                            <div class="d-flex justify-content-between align-items-center">
                                <span class="h5 fw-bold text-white mb-0">Total a Pagar</span>
                                <span class="h3 fw-bold text-gold mb-0" id="total_display">$0</span>
                            </div>
                        </div>

                        <button type="submit" class="btn btn-success btn-lg w-100 py-3 rounded-3 shadow">
                            CONTINUAR CON LA INVERSIÓN
                        </button>
                    </form>
                </div>
            </div>
        </div>
    </div>
</div>

<style>
    .btn-outline-gold {
        color: #D4AF37;
        border-color: #D4AF37;
    }
    .btn-outline-gold:hover {
        background-color: #D4AF37;
        color: #000;
    }
    .form-control:focus, .form-select:focus {
        background-color: #000;
        color: #fff;
        border-color: #D4AF37;
        box-shadow: 0 0 0 0.25rem rgba(212, 175, 55, 0.25);
    }
</style>

<script>
    let discountPct = 0;

    function calculateTotal() {
        const projectSelect = document.getElementById('id_proyecto');
        const qtyInput = document.getElementById('id_cantidad_tokens');
        
        let subtotal = 0;
        if (projectSelect.selectedIndex > 0) {
            const price = parseFloat(projectSelect.options[projectSelect.selectedIndex].dataset.price);
            subtotal = price * parseInt(qtyInput.value);
        }
        
        const discount = subtotal * (discountPct / 100);
        const total = subtotal - discount;

        document.getElementById('subtotal_display').innerText = '$' + subtotal.toLocaleString();
        document.getElementById('total_display').innerText = '$' + total.toLocaleString();
        
        if (discountPct > 0) {
            document.getElementById('discount_row').classList.remove('d-none');
            document.getElementById('discount_pct').innerText = discountPct;
            document.getElementById('discount_display').innerText = '-$' + discount.toLocaleString();
        } else {
            document.getElementById('discount_row').classList.add('d-none');
        }
    }

    function updateQty(delta) {
        const input = document.getElementById('id_cantidad_tokens');
        let newVal = parseInt(input.value) + delta;
        if (newVal < 1) newVal = 1;
        input.value = newVal;
        calculateTotal();
    }

    async function applyCoupon() {
        const code = document.getElementById('coupon_code').value;
        const msg = document.getElementById('coupon_msg');
        
        if (!code) return;

        try {
            const response = await fetch(`/validate-coupon/?code=${code}`);
            const data = await response.json();
            
            if (data.valid) {
                discountPct = data.discount;
                document.getElementById('id_coupon').value = data.id;
                msg.innerHTML = `<span class="text-success fw-bold">Cupón aplicado: ${data.discount}% de descuento</span>`;
                calculateTotal();
            } else {
                discountPct = 0;
                document.getElementById('id_coupon').value = '';
                msg.innerHTML = `<span class="text-danger">${data.message || 'Cupón inválido'}</span>`;
                calculateTotal();
            }
        } catch (e) {
            console.error('Error applying coupon', e);
        }
    }

    document.getElementById('id_proyecto').addEventListener('change', calculateTotal);
    document.getElementById('id_cantidad_tokens').addEventListener('input', calculateTotal);
    
    // Auto-init total
    calculateTotal();
</script>
{% endblock %}
"""

# --- 2. ADMIN PROJECT FORM ---
ADMIN_PROJECT_FORM_CONTENT = """{% extends 'booking/admin/base_admin.html' %}
{% load humanize %}

{% block title %}Editar Proyecto{% endblock %}
{% block page_title %}{% if proyecto %}Editar {{ proyecto.nombre }}{% else %}Nuevo Proyecto{% endif %}{% endblock %}

{% block content %}
<div class="glass-panel rounded-2xl p-8 max-w-4xl mx-auto border border-gold-500/20 shadow-2xl">
    <form method="POST" enctype="multipart/form-data" class="space-y-8">
        {% csrf_token %}
        
        <div class="grid grid-cols-1 md:grid-cols-2 gap-8">
            <!-- Global Info -->
            <div class="space-y-6">
                <h3 class="text-lg font-bold text-gold-500 border-b border-gold-500/20 pb-2">Información Básica</h3>
                
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Nombre del Proyecto</label>
                    <input type="text" name="nombre" value="{{ proyecto.nombre|default:'' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Ubicación</label>
                    <input type="text" name="ubicacion" value="{{ proyecto.ubicacion|default:'' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>

                <div class="grid grid-cols-2 gap-4">
                    <div>
                        <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Precio Token (USD)</label>
                        <input type="number" name="precio_token" value="{{ proyecto.precio_token|default:'100' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                    </div>
                    <div>
                        <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Tokens Totales</label>
                        <input type="number" name="tokens_totales" value="{{ proyecto.tokens_totales|default:'1000' }}" required class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                    </div>
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">Rentabilidad Estimada</label>
                    <input type="text" name="rentabilidad_estimada" value="{{ proyecto.rentabilidad_estimada|default:'12-18% Anual' }}" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none">
                </div>
            </div>

            <!-- Multimedia & Status -->
            <div class="space-y-6">
                <h3 class="text-lg font-bold text-gold-500 border-b border-gold-500/20 pb-2">Multimedia y Estado</h3>
                
                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">URL Imagen Portada (G-Drive/URL)</label>
                    <input type="url" name="imagen_portada_url" value="{{ proyecto.imagen_portada_url|default:'' }}" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-3 text-white focus:border-gold-500 outline-none" placeholder="https://...">
                </div>

                <div>
                    <label class="block text-xs font-bold text-gray-400 uppercase mb-2">O Subir Imagen</label>
                    <input type="file" name="imagen_portada" class="w-full bg-dark-900 border border-gray-700 rounded-xl p-2 text-gray-400 file:mr-4 file:py-2 file:px-4 file:rounded-lg file:border-0 file:text-sm file:font-semibold file:bg-gold-500 file:text-dark-900">
                </div>

                <div class="p-4 bg-dark-800 rounded-xl border border-gray-700">
                    <label class="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="activo" {% if proyecto.activo|default:True %}checked{% endif %} class="w-5 h-5 accent-gold-500">
                        <span class="text-sm text-white font-medium">Proyecto Activo (Visible en Landing)</span>
                    </label>
                </div>

                <div class="p-4 bg-dark-800 rounded-xl border border-gray-700">
                    <label class="flex items-center gap-3 cursor-pointer">
                        <input type="checkbox" name="financiamiento_activo" {% if proyecto.financiamiento_activo|default:True %}checked{% endif %} class="w-5 h-5 accent-gold-500">
                        <span class="text-sm text-white font-medium">Habilitar Venta de Tokens</span>
                    </label>
                </div>
            </div>
        </div>

        <div class="pt-8 border-t border-gray-800 flex justify-end gap-4">
            <a href="{% url 'admin_projects' %}" class="px-6 py-3 text-gray-400 hover:text-white transition-colors">Cancelar</a>
            <button type="submit" class="px-10 py-3 bg-gold-600 hover:bg-gold-500 text-black font-bold rounded-xl shadow-lg transition-all transform hover:scale-105 active:scale-95">
                GUARDAR PROYECTO
            </button>
        </div>
    </form>
</div>
{% endblock %}
"""

def main():
    # Write reservation_form.html
    with open(os.path.join(TEMPLATE_DIR, 'reservation_form.html'), 'w', encoding='utf-8') as f:
        f.write(RESERVATION_FORM_CONTENT)
    print(f"[FIXED] reservation_form.html")

    # Write admin/project_form.html
    with open(os.path.join(ADMIN_TEMPLATE_DIR, 'admin_project_form.html'), 'w', encoding='utf-8') as f:
        f.write(ADMIN_PROJECT_FORM_CONTENT)
    print(f"[FIXED] admin_project_form.html")

if __name__ == '__main__':
    main()

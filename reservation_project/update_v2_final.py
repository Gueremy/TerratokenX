import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'

# Refined content: 
# 1. Removed official-header.
# 2. Logic to focus on 'proyecto' if provided, otherwise 'proyectos_activos'.
# 3. Clean structure.

full_content = """{% extends 'booking/base.html' %}
{% load static %}
{% load humanize %}

{% block title %}Gateway RWA — TerraTokenX{% endblock %}

{% block extra_css %}
<style>
    :root {
        --gold-glow: rgba(212, 175, 55, 0.4);
        --bg-black: #050505;
        --panel-bg: #0d0d0d;
        --border-color: #222;
    }

    body { background-color: var(--bg-black); color: #fff; font-family: 'Inter', sans-serif; }

    /* Wizard Steps */
    .step-circle {
        width: 32px;
        height: 32px;
        border-radius: 50%;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        margin-bottom: 8px;
        transition: all 0.3s ease;
        border: 2px solid #333;
        background: #111;
        color: #666;
    }
    .step-active .step-circle {
        background: #d4af37;
        border-color: #d4af37;
        color: #000;
        box-shadow: 0 0 15px var(--gold-glow);
    }
    .step-label { font-size: 0.65rem; font-weight: bold; text-transform: uppercase; color: #666; letter-spacing: 1px; }
    .step-active .step-label { color: #d4af37; }

    /* Asset Selection Card */
    .asset-card {
        background: var(--panel-bg);
        border: 1px solid var(--border-color);
        border-radius: 12px;
        overflow: hidden;
        margin-bottom: 30px;
    }
    .asset-card-header {
        border-bottom: 1px solid var(--border-color);
        padding: 20px 25px;
    }
    .asset-visual {
        background: linear-gradient(180deg, #111 0%, #000 100%);
        height: 250px;
        display: flex;
        align-items: center;
        justify-content: center;
        position: relative;
        border-radius: 8px;
        margin: 20px;
        border: 1px solid #222;
        overflow: hidden;
    }
    .asset-visual img { width: 100%; height: 100%; object-fit: cover; opacity: 0.6; }
    
    .asset-info-grid {
        display: grid;
        grid-template-columns: 1fr 1fr;
        gap: 15px;
        padding: 0 20px;
    }
    .info-box {
        background: #111;
        border: 1px solid #222;
        padding: 15px;
        border-radius: 8px;
    }
    .info-label { font-size: 0.65rem; color: #888; text-transform: uppercase; font-weight: bold; margin-bottom: 4px; }
    .info-value { font-size: 1.4rem; font-weight: bold; }

    /* Quantity Selector */
    .qty-selector {
        background: #111;
        border: 1px solid #333;
        border-radius: 8px;
        display: flex;
        align-items: center;
        padding: 10px;
        margin: 20px;
    }
    .qty-btn {
        background: #222;
        border: none;
        color: #fff;
        width: 40px;
        height: 40px;
        border-radius: 6px;
        display: flex;
        align-items: center;
        justify-content: center;
        font-weight: bold;
        transition: all 0.2s;
    }
    .qty-btn:hover { background: #d4af37; color: #000; }
    .qty-input {
        background: transparent;
        border: none;
        color: #fff;
        text-align: center;
        flex-grow: 1;
        font-weight: bold;
        font-size: 1.5rem;
        width: 50px;
    }

    /* Total Bar */
    .total-bar {
        background: rgba(212, 175, 55, 0.05);
        border-top: 1px solid rgba(212, 175, 55, 0.1);
        padding: 20px 30px;
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-top: 20px;
    }

    /* Primary Gold Button */
    .btn-gold {
        background: #d4af37;
        color: #000;
        border: none;
        border-radius: 8px;
        padding: 18px;
        font-weight: bold;
        width: calc(100% - 40px);
        margin: 0 20px 20px 20px;
        transition: all 0.3s ease;
        text-transform: uppercase;
        letter-spacing: 1px;
        font-size: 0.95rem;
    }
    .btn-gold:hover { background: #e5c453; transform: translateY(-2px); box-shadow: 0 5px 20px var(--gold-glow); }
    .btn-gold:disabled { background: #222; color: #555; transform: none; box-shadow: none; cursor: not-allowed; }

    /* Warning Block */
    .separation-block {
        background: rgba(212, 175, 55, 0.03);
        border: 1px solid rgba(212, 175, 55, 0.1);
        padding: 20px;
        margin: 25px 0;
        border-radius: 12px;
    }

    .anti-phishing {
        background: #000;
        border: 1px dashed #333;
        padding: 12px;
        text-align: center;
        font-size: 0.75rem;
        color: #777;
        border-radius: 10px;
        line-height: 1.4;
    }
    .official-url { color: #fff; text-decoration: underline; font-weight: bold; }

    [x-cloak] { display: none !important; }

    /* Custom Input Styles */
    .form-control-custom {
        background: #000;
        border: 1px solid #333;
        color: #fff;
        padding: 15px;
        border-radius: 8px;
        font-size: 1rem;
    }
    .form-control-custom:focus {
        border-color: #d4af37;
        outline: none;
        box-shadow: 0 0 10px rgba(212, 175, 55, 0.1);
    }
</style>
{% endblock %}

{% block content %}
<div x-data="rwaWizard()" x-init="init()" x-cloak>

    <div class="row justify-content-center pt-5">
        <div class="col-lg-7 col-xl-6">

            <!-- Step Indicators -->
            <div class="d-flex justify-content-between mb-5">
                <div class="text-center flex-grow-1" :class="step >= 1 ? 'step-active' : ''">
                    <div class="step-circle mx-auto">1</div>
                    <div class="step-label">Proyecto</div>
                </div>
                <div class="text-center flex-grow-1" :class="step >= 2 ? 'step-active' : ''">
                    <div class="step-circle mx-auto">2</div>
                    <div class="step-label">Identidad</div>
                </div>
                <div class="text-center flex-grow-1" :class="step >= 3 ? 'step-active' : ''">
                    <div class="step-circle mx-auto">3</div>
                    <div class="step-label">Legal</div>
                </div>
                <div class="text-center flex-grow-1" :class="step >= 4 ? 'step-active' : ''">
                    <div class="step-circle mx-auto">4</div>
                    <div class="step-label">Pago</div>
                </div>
            </div>

            <!-- Anti-Phishing Banner v2 -->
            <div class="anti-phishing mb-5">
                <div class="d-flex align-items-center justify-content-center gap-2">
                    <i class="fas fa-shield-alt text-warning"></i>
                    <span>Verifica siempre la URL oficial: <span class="official-url">terratokenx.com</span></span>
                </div>
            </div>

            <form method="post" id="rwaForm" @submit.prevent="handleSubmit">
                {% csrf_token %}

                <!-- STEP 1: ASSET SELECTION -->
                <div x-show="step === 1" x-transition>
                    <div class="asset-card shadow-2xl">
                        <div class="asset-card-header">
                            <h5 class="m-0 d-flex align-items-center gap-2 font-bold uppercase tracking-wider">
                                <i class="fas fa-building text-gold"></i> Selección del Activo
                            </h5>
                        </div>

                        <!-- Asset Details Section -->
                        <div class="p-0">
                            {% if proyecto %}
                                <!-- Showing specific project from slug -->
                                <div class="asset-visual">
                                    {% if proyecto.imagen_portada_url %}
                                        <img src="{{ proyecto.imagen_portada_url }}">
                                    {% else %}
                                        <div class="bg-dark w-100 h-100 d-flex align-items-center justify-content-center">
                                            <i class="far fa-image fa-3x text-secondary"></i>
                                        </div>
                                    {% endif %}
                                    <div class="position-absolute bottom-0 start-0 p-4 w-100" style="background: linear-gradient(0deg, #0d0d0d 0%, transparent 100%);">
                                        <h3 class="text-white fw-bold mb-0">{{ proyecto.nombre }}</h3>
                                        <span class="text-gold small fw-bold uppercase">Reserva de Cupo</span>
                                    </div>
                                    <input type="hidden" name="proyecto" value="{{ proyecto.id }}">
                                </div>

                                <div class="asset-info-grid">
                                    <div class="info-box">
                                        <div class="info-label">PRECIO TOKEN</div>
                                        <div class="info-value text-white">$<span x-text="formatNumber({{ proyecto.precio_token }})"></span> USD</div>
                                    </div>
                                    <div class="info-box">
                                        <div class="info-label">RENTABILIDAD</div>
                                        <div class="info-value text-success">{{ proyecto.rentabilidad_estimada }}</div>
                                    </div>
                                </div>
                                
                                <div x-init="projectPrice = {{ proyecto.precio_token }}; projectName = '{{ proyecto.nombre|escapejs }}'; calculateTotal()"></div>
                            {% else %}
                                <!-- Fallback if no specific project selected -->
                                {% for p in proyectos_activos|slice:":1" %}
                                <div class="asset-visual">
                                    {% if p.imagen_portada_url %}
                                        <img src="{{ p.imagen_portada_url }}">
                                    {% else %}
                                        <div class="bg-dark w-100 h-100 d-flex align-items-center justify-content-center">
                                            <i class="far fa-image fa-3x text-secondary"></i>
                                        </div>
                                    {% endif %}
                                    <div class="position-absolute bottom-0 start-0 p-4 w-100" style="background: linear-gradient(0deg, #0d0d0d 0%, transparent 100%);">
                                        <h3 class="text-white fw-bold mb-0">{{ p.nombre }}</h3>
                                        <span class="text-gold small fw-bold uppercase">Reserva de Cupo</span>
                                    </div>
                                    <input type="hidden" name="proyecto" value="{{ p.id }}">
                                </div>

                                <div class="asset-info-grid">
                                    <div class="info-box">
                                        <div class="info-label">PRECIO TOKEN</div>
                                        <div class="info-value text-white">$<span x-text="formatNumber({{ p.precio_token }})"></span> USD</div>
                                    </div>
                                    <div class="info-box">
                                        <div class="info-label">RENTABILIDAD</div>
                                        <div class="info-value text-success">{{ p.rentabilidad_estimada }}</div>
                                    </div>
                                </div>
                                <div x-init="projectPrice = {{ p.precio_token }}; projectName = '{{ p.nombre|escapejs }}'; calculateTotal()"></div>
                                {% endfor %}
                            {% endif %}

                            <div class="mt-4 px-4 text-center">
                                <p class="text-muted small mb-2 text-uppercase fw-bold tracking-widest" style="font-size: 0.6rem;">¿Cuántos tokens deseas adquirir?</p>
                            </div>
                            <div class="qty-selector">
                                <button type="button" class="qty-btn" @click="changeQty(-1)"><i class="fas fa-minus"></i></button>
                                <input type="number" name="cantidad_tokens" x-model="qty" @input="calculateTotal()" class="qty-input">
                                <button type="button" class="qty-btn" @click="changeQty(1)"><i class="fas fa-plus"></i></button>
                            </div>

                            <div class="total-bar">
                                <span class="text-muted fw-bold small text-uppercase" style="letter-spacing: 1px;">Total a Pagar:</span>
                                <span class="h3 text-gold m-0 font-bold" x-text="'$' + formatNumber(total) + ' USD'"></span>
                            </div>

                            <button type="button" class="btn-gold shadow-lg" @click="step = 2">
                                Continuar a Identidad <i class="fas fa-arrow-right ms-2"></i>
                            </button>
                        </div>
                    </div>

                    <div class="separation-block">
                        <div class="d-flex gap-3">
                            <i class="fas fa-exclamation-circle text-gold fa-lg mt-1"></i>
                            <div>
                                <strong class="text-white d-block mb-1">Ecosistema RWA</strong>
                                <p class="small text-muted mb-0" style="line-height: 1.5;">
                                    Este activo digital es un <strong>Token de Activo (Security Token)</strong>. Su valor está vinculado exclusivamente al rendimiento inmobiliario del proyecto.
                                </p>
                            </div>
                        </div>
                    </div>

                    <div class="row g-3 mb-5 px-1">
                        <div class="col-6">
                            <a href="#" class="bg-dark p-3 rounded border border-secondary border-opacity-30 d-flex align-items-center gap-3 h-100 text-decoration-none hover-gold transition-all">
                                <i class="far fa-file-pdf text-danger fa-lg"></i>
                                <span class="small fw-bold text-white">Whitepaper</span>
                            </a>
                        </div>
                        <div class="col-6">
                            <a href="#" class="bg-dark p-3 rounded border border-secondary border-opacity-30 d-flex align-items-center gap-3 h-100 text-decoration-none hover-gold transition-all">
                                <i class="fas fa-exclamation-triangle text-warning fa-lg"></i>
                                <span class="small fw-bold text-white">Riesgos</span>
                            </a>
                        </div>
                    </div>
                </div>

                <!-- STEP 2: IDENTITY / KYC -->
                <div x-show="step === 2" x-transition x-cloak>
                    <div class="asset-card">
                        <div class="asset-card-header">
                            <h5 class="m-0 uppercase tracking-widest"><i class="fas fa-user-shield text-gold me-2"></i>Tus Datos</h5>
                        </div>
                        <div class="p-4 p-md-5">
                            <div class="row g-4">
                                <div class="col-md-6">
                                    <label class="info-label mb-2">NOMBRE COMPLETO</label>
                                    {% if user.is_authenticated %}
                                    <input type="text" name="nombre" class="form-control-custom w-100" value="{{ user.first_name }} {{ user.last_name }}" required>
                                    {% else %}
                                    <input type="text" name="nombre" class="form-control-custom w-100" placeholder="Ej: Juan Pérez" required>
                                    {% endif %}
                                </div>
                                <div class="col-md-6">
                                    <label class="info-label mb-2">EMAIL</label>
                                    {% if user.is_authenticated %}
                                    <input type="email" name="correo" class="form-control-custom w-100" value="{{ user.email }}" required>
                                    {% else %}
                                    <input type="email" name="correo" class="form-control-custom w-100" placeholder="correo@ejemplo.com" required>
                                    {% endif %}
                                </div>
                                <div class="col-md-12">
                                    <label class="info-label mb-2">RUT / ID NACIONAL</label>
                                    <input type="text" name="rut" class="form-control-custom w-100" placeholder="12.345.678-K" required>
                                </div>
                                <div class="col-md-12">
                                    <label class="info-label mb-2">TELÉFONO</label>
                                    <input type="text" name="telefono" class="form-control-custom w-100" placeholder="+56 9 ..." required>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 d-flex gap-3">
                            <button type="button" class="btn btn-outline-secondary flex-grow-1 p-3 rounded-lg font-bold" @click="step = 1">ATRÁS</button>
                            <button type="button" class="btn-gold flex-grow-1 m-0" @click="step = 3">SIGUIENTE</button>
                        </div>
                    </div>
                </div>

                <!-- STEP 3: LEGAL -->
                <div x-show="step === 3" x-transition x-cloak>
                    <div class="asset-card">
                        <div class="asset-card-header">
                            <h5 class="m-0 uppercase tracking-widest"><i class="fas fa-file-contract text-gold me-2"></i>Legal & T&C</h5>
                        </div>
                        <div class="p-4 p-md-5 text-center">
                            <div class="bg-black p-4 rounded-lg border border-secondary mb-5">
                                <div class="text-muted small uppercase mb-1">Total Reserva</div>
                                <div class="h2 text-gold font-bold" x-text="'$' + formatNumber(total) + ' USD'"></div>
                            </div>

                            <div class="text-start space-y-4">
                                <div class="form-check mb-4 custom-check">
                                    <input class="form-check-input bg-black border-secondary" type="checkbox" id="terms" required x-model="tcAccepted">
                                    <label class="form-check-label small text-muted ms-2" for="terms">
                                        He leído y acepto los <a href="#" class="text-gold text-decoration-none">Términos de Inversión</a> y la <a href="#" class="text-gold text-decoration-none">Política de Privacidad</a>.
                                    </label>
                                </div>
                                <div class="form-check mb-4 custom-check">
                                    <input class="form-check-input bg-black border-secondary" type="checkbox" id="eligibility" required x-model="eligibleAccepted">
                                    <label class="form-check-label small text-muted ms-2" for="eligibility">
                                        Declaro bajo juramento la licitud de los fondos y cumplimiento de elegibilidad.
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 d-flex gap-3">
                            <button type="button" class="btn btn-outline-secondary flex-grow-1 p-3 rounded-lg font-bold" @click="step = 2">ATRÁS</button>
                            <button type="button" class="btn-gold flex-grow-1 m-0" @click="step = 4" :disabled="!tcAccepted || !eligibleAccepted">CONTINUAR AL PAGO</button>
                        </div>
                    </div>
                </div>

                <!-- STEP 4: PAYMENT -->
                <div x-show="step === 4" x-transition x-cloak>
                    <div class="asset-card">
                        <div class="asset-card-header text-center">
                            <h5 class="m-0 uppercase tracking-widest">Gateway de Pago</h5>
                        </div>
                        <div class="p-4 p-md-5">
                            <div class="row g-4">
                                <div class="col-md-6">
                                    <label class="w-100 cursor-pointer">
                                        <input type="radio" name="metodo_pago" value="MP" class="d-none" x-model="paymentMethod">
                                        <div class="p-4 text-center rounded-lg border-2 transition-all h-100 d-flex flex-column align-items-center justify-content-center"
                                             :class="paymentMethod === 'MP' ? 'border-gold bg-dark' : 'border-secondary bg-black'">
                                            <i class="fas fa-credit-card fa-2x mb-3 text-primary"></i>
                                            <div class="fw-bold text-white uppercase" style="font-size: 0.8rem;">Mercado Pago</div>
                                            <div class="x-small text-muted mt-1" style="font-size: 0.6rem;">FIAT (TARJETAS)</div>
                                        </div>
                                    </label>
                                </div>
                                <div class="col-md-6">
                                    <label class="w-100 cursor-pointer">
                                        <input type="radio" name="metodo_pago" value="CRYPTO" class="d-none" x-model="paymentMethod">
                                        <div class="p-4 text-center rounded-lg border-2 transition-all h-100 d-flex flex-column align-items-center justify-content-center"
                                             :class="paymentMethod === 'CRYPTO' ? 'border-gold bg-dark' : 'border-secondary bg-black'">
                                            <i class="fab fa-bitcoin fa-2x mb-3 text-warning"></i>
                                            <div class="fw-bold text-white uppercase" style="font-size: 0.8rem;">Criptomonedas</div>
                                            <div class="x-small text-muted mt-1" style="font-size: 0.6rem;">USDT / BTC / ETH</div>
                                        </div>
                                    </label>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 d-flex gap-3">
                            <button type="button" class="btn btn-outline-secondary flex-grow-1 p-3 rounded-lg font-bold" @click="step = 3">ATRÁS</button>
                            <button type="submit" class="btn-gold flex-grow-1 m-0">FINALIZAR COMPRA</button>
                        </div>
                    </div>
                </div>

            </form>

            <div class="mt-4 pb-5 text-center d-flex flex-wrap justify-content-center gap-4">
                <a href="#" class="text-muted small hover-gold text-decoration-none uppercase tracking-tighter" style="font-size: 0.65rem;">Términos</a>
                <a href="#" class="text-muted small hover-gold text-decoration-none uppercase tracking-tighter" style="font-size: 0.65rem;">Privacidad</a>
                <a href="#" class="text-muted small hover-gold text-decoration-none uppercase tracking-tighter" style="font-size: 0.65rem;">Mapa de Riesgos</a>
                <a href="#" class="text-muted small hover-gold text-decoration-none uppercase tracking-tighter" style="font-size: 0.65rem;">Contáctanos</a>
            </div>

        </div>
    </div>
</div>

<script src="https://unpkg.com/alpinejs@3.x.x/dist/cdn.min.js" defer></script>

<script>
    function rwaWizard() {
        return {
            step: 1,
            qty: 1,
            projectPrice: 0,
            projectName: '',
            total: 0,
            tcAccepted: false,
            eligibleAccepted: false,
            paymentMethod: 'MP',
            
            init() {},

            changeQty(delta) {
                this.qty = Math.max(1, parseInt(this.qty) + delta);
                this.calculateTotal();
            },

            calculateTotal() {
                this.total = this.projectPrice * this.qty;
            },

            formatNumber(num) {
                if (!num) return "0";
                return num.toLocaleString('en-US');
            },

            handleSubmit() {
                document.getElementById('rwaForm').submit();
            }
        }
    }
</script>

<style>
    .hover-gold:hover { color: #d4af37 !important; }
    .x-small { font-size: 0.75rem; }
    .custom-check .form-check-input:checked { background-color: #d4af37; border-color: #d4af37; }
    .qty-input::-webkit-outer-spin-button,
    .qty-input::-webkit-inner-spin-button { -webkit-appearance: none; margin: 0; }
</style>
{% endblock %}"""

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(full_content)

print("File updated: navbar/header removed, project logic refined.")

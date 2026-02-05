
import os
import re

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\comprar_creditos.html'

def fix_credits_template():
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            content = f.read()

        # 1. Fix Precio Principal (Pattern multiline)
        # Buscar {{ tier.precio... |intcomma \n }} y reemplazar por single line
        # Usamos regex robusto para capturar variaciones de espacios
        
        # Pattern 1: tier.precio_por_1000_creditos|intcomma
        pattern1 = r'\{\{\s*tier\.precio_por_1000_creditos\|intcomma\s*\}\}'
        content = re.sub(pattern1, '{{ tier.precio_por_1000_creditos|intcomma }}', content)
        # Force specific broken string just in case regex misses due to invisible chars
        content = content.replace('{{ tier.precio_por_1000_creditos|intcomma\n                            }}', '{{ tier.precio_por_1000_creditos|intcomma }}')

        # Pattern 2: 1000|intcomma
        pattern2 = r'\{\{\s*1000\|intcomma\s*\}\}'
        content = re.sub(pattern2, '{{ 1000|intcomma }}', content)

        # Pattern 3: Cap creditos
        pattern3 = r'\{\{\s*tier\.cap_creditos\|intcomma\s*\}\}'
        content = re.sub(pattern3, '{{ tier.cap_creditos|intcomma }}', content)
        # Force specific broken string
        content = content.replace('Cap: ${{ tier.cap_creditos|intcomma\n                            }}', 'Cap: ${{ tier.cap_creditos|intcomma }}')
        content = content.replace('Cap: ${{ tier.cap_creditos|intcomma }}', 'Cap: ${{ tier.cap_creditos|intcomma }}') # Normalize

        # Pattern 4: Ahorro calc
        # {{ 1000|add:"-"|add:tier.precio_por_1000_creditos }}
        # Simplificación: Django templates son frágiles con pipes y args complejos si hay espacios raros.
        # Reescribimos el bloque completo para asegurar.
        # Buscamos el bloque "Ahorra $..."
        
        # Fix general: collapse ALL {{ ... }} into single line if possible?
        # Better: just fix known broken ones manually in the string.
        
        # Re-write the whole file content with a clean version to be 100% sure
        # This is safer than regex patching for a small file
        clean_html = """{% extends 'booking/base.html' %}
{% load humanize %}

{% block title %}Comprar Créditos - TerraTokenX{% endblock %}

{% block content %}
<div class="container py-5">
    <div class="text-center mb-5">
        <h1 class="display-5 fw-bold text-white">Comprar Créditos</h1>
        <p class="lead text-muted">Elige tu paquete y obtén descuentos exclusivos</p>
    </div>

    <!-- Saldo Actual -->
    {% if tier_info %}
    <div class="alert alert-dark text-center mb-4">
        <strong>Tu saldo actual:</strong>
        <span class="text-success fs-4">${{ tier_info.saldo|floatformat:0|intcomma }}</span>
        <span class="badge bg-secondary ms-2">{{ tier_info.nombre_display }}</span>
    </div>
    {% endif %}

    <!-- Paquetes -->
    <div class="row justify-content-center">
        {% for tier in tiers %}
        <div class="col-md-6 col-lg-4 mb-4">
            <div class="card bg-dark text-white h-100 border-{% if tier.nombre == 'SILVER' %}light{% else %}secondary{% endif %}">
                <div class="card-header text-center py-3">
                    <h4 class="mb-0">
                        {% if tier.nombre == 'SILVER' %}
                        <i class="fas fa-medal me-2" style="color: #C0C0C0;"></i>
                        {% else %}
                        <i class="fas fa-shield-alt me-2" style="color: #CD7F32;"></i>
                        {% endif %}
                        {{ tier.get_nombre_display }}
                    </h4>
                </div>
                <div class="card-body text-center">
                    <div class="mb-3">
                        <span class="display-6 fw-bold text-success">${{ tier.precio_por_1000_creditos|intcomma }}</span>
                        <span class="text-muted">USD</span>
                    </div>
                    <p class="lead">
                        Obtén <strong class="text-warning">${{ 1000|intcomma }}</strong> en créditos
                    </p>
                    <p class="text-muted small">
                        {% with descuento=1000|add:"-"|add:tier.precio_por_1000_creditos %}
                        <span class="badge bg-success">Ahorra ${{ descuento }} USD</span>
                        {% endwith %}
                    </p>

                    <hr class="border-secondary">

                    <ul class="list-unstyled text-start small mb-4">
                        <li class="mb-2"><i class="fas fa-check text-success me-2"></i>Cap: ${{ tier.cap_creditos|intcomma }}</li>
                        <li class="mb-2"><i class="fas fa-check text-success me-2"></i>{{ tier.descuento_fees }}% descuento en fees</li>
                        <li class="mb-2"><i class="fas fa-check text-success me-2"></i>Válidos por 12 meses</li>
                    </ul>
                </div>
                <div class="card-footer bg-transparent border-0 pb-4">
                    <form method="POST" action="{% url 'comprar_creditos' %}">
                        {% csrf_token %}
                        <input type="hidden" name="tier" value="{{ tier.nombre }}">
                        <input type="hidden" name="cantidad" value="1">

                        <div class="d-grid gap-2">
                            <button type="submit" name="metodo" value="MP" class="btn btn-success btn-lg">
                                <i class="fab fa-cc-visa me-1"></i>Pagar con Mercado Pago
                            </button>
                            <button type="submit" name="metodo" value="CRYPTO" class="btn btn-outline-warning">
                                <i class="fab fa-bitcoin me-1"></i>Pagar con Crypto (USDC/USDT)
                            </button>
                        </div>
                    </form>
                </div>
            </div>
        </div>
        {% empty %}
        <div class="col-12 text-center">
            <div class="alert alert-warning">
                <i class="fas fa-info-circle me-2"></i>
                No hay paquetes disponibles en este momento.
                <a href="{% url 'solicitar_vip' %}" class="alert-link">Solicita acceso VIP</a>.
            </div>
        </div>
        {% endfor %}
    </div>

    <!-- CTA VIP -->
    <div class="text-center mt-5">
        <div class="card bg-gradient" style="background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%); border: 2px solid #ffd700;">
            <div class="card-body py-5">
                <h3 class="text-warning"><i class="fas fa-crown me-2"></i>¿Buscas más?</h3>
                <p class="text-white mb-4">Accede a los tiers Gold y Black con hasta 40% de descuento y beneficios exclusivos.</p>
                <a href="{% url 'solicitar_vip' %}" class="btn btn-warning btn-lg">
                    <i class="fab fa-whatsapp me-1"></i>Contactar Concierge VIP
                </a>
            </div>
        </div>
    </div>
</div>
{% endblock %}
"""
        with open(file_path, 'w', encoding='utf-8') as f:
            f.write(clean_html)
        print("✅ FORCE FIX: comprar_creditos.html overwritten successfully.")
        
    except Exception as e:
        print(f"❌ ERROR: {e}")

if __name__ == "__main__":
    fix_credits_template()

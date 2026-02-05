import os

file_path = r'c:\Users\Guere\OneDrive\Escritorio\WAS DE PROGRAMACION\adaptar sistemas de reservas joan\chelooficial\reservation_project\booking\templates\booking\reservation_form_v2.html'

with open(file_path, 'r', encoding='utf-8') as f:
    content = f.read()

# I will replace Step 2 section with a more complete one.

old_step_2 = """                <!-- STEP 2: IDENTITY / KYC -->
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
                </div>"""

new_step_2 = """                <!-- STEP 2: IDENTITY / KYC -->
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
                                <div class="col-md-6">
                                    <label class="info-label mb-2">RUT / ID NACIONAL</label>
                                    <input type="text" name="rut" class="form-control-custom w-100" placeholder="12.345.678-K" required>
                                </div>
                                <div class="col-md-6">
                                    <label class="info-label mb-2">TELÉFONO</label>
                                    <input type="text" name="telefono" class="form-control-custom w-100" placeholder="+56 9 1234 5678" required>
                                </div>
                                <div class="col-md-12">
                                    <label class="info-label mb-2">DIRECCIÓN (Requerido para el contrato)</label>
                                    <input type="text" name="direccion" class="form-control-custom w-100" placeholder="Calle, Número, Ciudad" required>
                                </div>

                                <!-- Persona Jurídica Toggle -->
                                <div class="col-md-12 mt-3">
                                    <div class="form-check custom-check">
                                        <input class="form-check-input bg-black border-secondary" type="checkbox" id="es_empresa" name="es_empresa" x-model="isCompany">
                                        <label class="form-check-label small text-muted ms-2" for="es_empresa">
                                            Deseo invertir como Persona Jurídica (Empresa)
                                        </label>
                                    </div>
                                </div>

                                <!-- Campos Empresa (Collapsible) -->
                                <div class="col-md-12" x-show="isCompany" x-transition>
                                    <div class="row g-4 mt-1 p-3 rounded-lg border border-secondary border-opacity-30 bg-black">
                                        <div class="col-md-6">
                                            <label class="info-label mb-2">RAZÓN SOCIAL</label>
                                            <input type="text" name="razon_social" class="form-control-custom w-100" placeholder="Mi Empresa S.A.">
                                        </div>
                                        <div class="col-md-6">
                                            <label class="info-label mb-2">RUT EMPRESA</label>
                                            <input type="text" name="rut_empresa" class="form-control-custom w-100" placeholder="76.123.456-7">
                                        </div>
                                        <div class="col-md-12">
                                            <label class="info-label mb-2">CARGO REPRESENTANTE</label>
                                            <input type="text" name="cargo_representante" class="form-control-custom w-100" placeholder="Ej: Gerente General">
                                        </div>
                                    </div>
                                </div>
                            </div>
                        </div>
                        <div class="p-4 d-flex gap-3">
                            <button type="button" class="btn btn-outline-secondary flex-grow-1 p-3 rounded-lg font-bold" @click="step = 1">ATRÁS</button>
                            <button type="button" class="btn-gold flex-grow-1 m-0" @click="step = 3">SIGUIENTE</button>
                        </div>
                    </div>
                </div>"""

# Update Alpine state
content = content.replace("paymentMethod: 'MP',", "paymentMethod: 'MP',\n            isCompany: false,")
content = content.replace(old_step_2, new_step_2)

with open(file_path, 'w', encoding='utf-8') as f:
    f.write(content)

print("Step 2 updated with address and company fields. Alpine state updated.")

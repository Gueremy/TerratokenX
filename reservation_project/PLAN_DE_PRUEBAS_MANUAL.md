# 🧪 MASTER TEST PLAN: TerraTokenX Agency Validation
> **Versión:** 2.0 (Release Candidate)
> **Objetivo:** Validación integral "End-to-End" del ecosistema TerraTokenX.
> **Nivel:** Exhaustivo (Agencia/Auditoría).

---

## 🏗️ 1. Preparación del Entorno
Antes de iniciar, asegura tener:
1.  Navegador en **Modo Incógnito** (para simular usuario nuevo sin cookies).
2.  Acceso al **Panel de Admin** en otra pestaña/navegador (logueado como Superuser).
3.  Correo temporal o alias (ej: `test+01@gmail.com`) para verificar emails.

---

## 👤 2. Flujo de Inversión "End-to-End"

### Escenario A: El Nuevo Inversor (Onboarding)
1.  **Landing Page & Navegación**
    *   Ingresa a la Home (`/`).
    *   Verifica que los Proyectos destacados carguen correctamente.
    *   Haz clic en "Ver Detalles" de un proyecto (ej: *Refugio Patagonia*).
    *   Intenta acceder a la pestaña "Documentos (Data Room)".
    *   ⭕ **Checkpoint:** Debe pedirte iniciar sesión o mostrar candados en documentos privados.

2.  **Registro de Usuario**
    *   Ve a `/registro/`.
    *   Completa el formulario.
    *   Intenta registrarte 4 veces seguidas rápidamente con datos falsos.
    *   ⭕ **Checkpoint (Seguridad):** El sistema debe bloquearte temporalmente por `Rate Limiting`.
    *   Espera o cambia de IP y completa un registro válido.
    *   ⭕ **Checkpoint:** Redirección inmediata al Dashboard (`/mi-cuenta/`). Tier inicial: **BRONZE**.

3.  **Configuración de Seguridad (KYC)**
    *   En Dashboard, observa el widget de "Estado KYC". Debe decir "No iniciado".
    *   Haz clic en "Verificar Identidad".
    *   Sube una foto cualquiera (JPG/PNG) para DNI Frente, Dorso y Selfie.
    *   Envía el formulario.
    *   ⭕ **Checkpoint:**
        *   Dashboard muestra estado "PENDIENTE" (Alerta amarilla).
        *   **Backend:** Verifica en carpeta `media/kyc/{user_id}/` que los archivos tengan nombres encriptados aleatorios (UUID).

---

## 💰 3. Operativa Financiera (Tokenización)

### Escenario B: Compra de Créditos (Ramp-On)
1.  **Compra Vía MercadoPago (Simulación)**
    *   Ve a `/creditos/`.
    *   Selecciona Pack **GOLD** (ej: 5000 créditos). Método: MercadoPago.
    *   Confirma la operación.
    *   ⭕ **Checkpoint:**
        *   Saldo en Dashboard aumenta inmediatamente.
        *   Tier cambia a **GOLD** (upgrade automático).
        *   Barra de progreso de Créditos se actualiza con animación.

2.  **Compra Vía Crypto (Transferencia USDT)**
    *   Selecciona Pack **STANDARD** (1000 créditos). Método: Crypto (USDT).
    *   Copia la dirección de wallet mostrada.
    *   Sube un "Hash de transacción" ficticio (ej: `0xaaaa...`).
    *   Envía.
    *   ⭕ **Checkpoint:**
        *   Mensaje: "Pago bajo revisión".
        *   Saldo **NO** aumenta todavía (requiere aprobación manual).

---

## 🛡️ 4. Gestión Administrativa (Back-Office)

### Escenario C: El Administrador (Auditoría y Aprobación)
1.  **Gestión de Seguridad (KYC)**
    *   Ve a `/admin-panel/users/` (o filtro de KYC pendientes).
    *   Revisa la solicitud del usuario del Escenario A.
    *   Haz clic en **Aprobar** (usando los nuevos modales o vista detalle).
    *   ⭕ **Checkpoint:** En Dashboard de usuario, el estado cambia a **VERIFICADO** (Verde).

2.  **Conciliación de Pagos (Crypto)**
    *   Ve a `/admin-panel/sales/` (Ventas).
    *   Ubica la transacción Crypto pendiente.
    *   Haz clic en "Verificar / Aprobar".
    *   ⭕ **Checkpoint:**
        *   El sistema acredita los créditos al usuario.
        *   Se genera registro en `AuditLog`.

3.  **Gestión VIP (Intervención Manual)**
    *   Ve a `/admin-panel/users/`.
    *   Busca al usuario.
    *   **Acción 1 (Tier):** Cámbialo manualmente a **DIAMOND** usando el botón de estrella.
    *   **Acción 2 (Saldo):** Dale un bono de 500 USD por "Compensación".
    *   **Acción 3 (Bloqueo):** Bloquéalo temporalmente.
    *   ⭕ **Checkpoint:** Intenta loguearte como ese usuario -> Debe dar error "Cuenta inactiva". Desbloquéalo para continuar.

4.  **Seguridad Admin (2FA - Si activado)**
    *   Si activaste 2FA, intenta entrar al `/admin/`.
    *   ⭕ **Checkpoint:** Debe pedirte el código OTP de Google Authenticator.

---

## 💎 5. Funcionalidades Premium & Seguridad

### Escenario D: Ciclo de Vida Avanzado
1.  **Inversión en Proyecto**
    *   Con saldo disponible, ve a un Proyecto.
    *   Invierte 2000 USD (Créditos).
    *   ⭕ **Checkpoint:**
        *   Saldo se descuenta.
        *   Aparece en "Mis Inversiones".
        *   **Cashback:** Si eres Diamond/Gold, verifica si recibiste un cashback automático (ver Historial).

2.  **Gestión de Wallet**
    *   En Dashboard, vincula una wallet `0x...`.
    *   Intenta eliminarla con el botón rojo "Eliminar Wallet".
    *   ⭕ **Checkpoint:**
        *   Pide confirmación.
        *   Wallet se borra exitosamente de la BD.

3.  **Expiración de Créditos (Validación Lógica)**
    *   Revisa la fecha de expiración de tus últimas compras en el Admin `/admin/booking/credittransaction/`.
    *   ⭕ **Checkpoint:**
        *   Compras siendo Standard/Gold: ~365 días (1 año).
        *   Compras siendo Diamond: ~540 días (1.5 años).

---

## 🏁 Criterio de Éxito Final
El sistema se considera **APTO PARA PRODUCCIÓN (Go-Live)** si:
1.  No hay errores 500 (Server Error) en ningún paso crítico.
2.  Los saldos financieros siempre cuadran.
3.  La seguridad administrativa (Audit Logs, Rate Limits) está activa y registrando eventos.

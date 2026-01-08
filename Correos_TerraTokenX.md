# CORREOS ELECTRÓNICOS - TerraTokenX

Este documento contiene los textos de todos los correos electrónicos que envía el sistema.
Los campos entre {{ }} son variables que se reemplazan automáticamente con los datos del cliente.

---

## 1. CORREO: RESERVA PENDIENTE (MERCADO PAGO)

**Cuándo se envía:** Cuando el cliente crea una reserva y selecciona Mercado Pago como método de pago, pero aún no ha pagado.

**Asunto:** Tu solicitud de reserva está pendiente de pago

**Contenido del correo:**

---

Hola **{{ reserva.nombre }}**,

Hemos recibido tu solicitud de reserva para la Preventa de TerraTokenX.

Tu orden **#{{ reserva.numero_reserva }}** ha sido creada exitosamente. Para asegurar tu cupo, por favor completa tu pago a través de **Mercado Pago**.

**Resumen de la Orden:**
- **Monto Total:** ${{ reserva.total }}
- **Método de Pago:** Mercado Pago

Si ya realizaste el pago, recibirás un correo de confirmación en breve.

Saludos,
**Equipo TerraTokenX**

---

---

## 2. CORREO: RESERVA PENDIENTE (CRYPTO)

**Cuándo se envía:** Cuando el cliente crea una reserva y selecciona Criptomoneda como método de pago.

**Asunto:** ⏳ Instrucciones para finalizar tu inversión en TerraTokenX

**Contenido del correo:**

---

Hola **{{ reserva.nombre }}**,

Hemos recibido tu solicitud de reserva para la Preventa de TerraTokenX.

Para confirmar tu cupo, por favor completa la transferencia del monto acordado a nuestra billetera oficial.

**Resumen de Orden:**
- **Orden:** #{{ reserva.numero_reserva }}
- **Monto a transferir:** ${{ reserva.total }} (Equivalente en Cripto)

**Datos de Transferencia (CryptoMarket):**
- **Wallet (USDT/BTC):** [AQUÍ VA LA WALLET QUE TE DARÁ JOAN]
- **Red:** [AQUÍ VA LA RED, EJ: TRC20]

**Importante:** Una vez realizada la transferencia, responde a este correo adjuntando el comprobante o Hash de la transacción para validar tu pago manualmente.

Quedamos atentos a tu comprobante.

Saludos,
**Equipo TerraTokenX**

---

---

## 3. CORREO: CONFIRMACIÓN DE PAGO

**Cuándo se envía:** Cuando el pago ha sido confirmado (ya sea automáticamente por Mercado Pago o manualmente por el administrador).

**Asunto:** ✅ Confirmación: Tu cupo en la Preventa TerraTokenX está asegurado

**Contenido del correo:**

---

Hola **{{ reserva.nombre }}**,

¡Bienvenido a TerraTokenX!

Confirmamos la recepción de tu pago por **${{ reserva.total }}**.

Has asegurado exitosamente tu posición en nuestra Preventa Exclusiva.

**Detalles de tu Inversión:**
- **Nº de Orden:** #{{ reserva.numero_reserva }}
- **Medio de Pago:** {{ reserva.metodo_pago }}
- **Estado:** Confirmado / Pagado

**¿Qué sigue ahora?** Tu participación ya está registrada en nuestra base de datos prioritaria. En Marzo, cuando lancemos la plataforma oficial, te contactaremos a este mismo correo para migrar tu saldo y entregarte tus Tokens digitales en tu dashboard personal.

Gracias por confiar en el futuro de la inversión inmobiliaria.

Si tienes dudas, contáctanos a nuestro WhatsApp: **+56 9 2883 9093**

Atentamente,
**El equipo de TerraTokenX**
Respaldo Legal y Tecnología Blockchain

---

---

## NOTAS PARA EDICIÓN

### Variables Dinámicas:
- `{{ reserva.nombre }}` → Nombre del cliente
- `{{ reserva.numero_reserva }}` → Número de orden (ej: ORD-2024-001)
- `{{ reserva.total }}` → Monto total en pesos
- `{{ reserva.metodo_pago }}` → Mercado Pago o Crypto

### Archivos de los correos:
Los archivos HTML de estos correos están en:
`booking/templates/booking/email/`

- `pending_reservation_mp.html` → Correo pendiente Mercado Pago
- `pending_reservation_crypto.html` → Correo pendiente Crypto
- `reservation_confirmation.html` → Correo de confirmación

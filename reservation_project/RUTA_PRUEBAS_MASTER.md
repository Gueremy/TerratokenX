# 🚀 PLAN MAESTRO DE VALIDACIÓN Y CORRECCIÓN (Fases 1-11)
**Estado:** Actualizado con últimos parches (XSS, Drops, MercadoPago, Dashboard).
**Objetivo:** Recorrer el sistema en orden y certificar cada módulo tras las reparaciones.

---

## 🟢 FASE 1: ACCESO (Login & Registro)
**Estado:** ✅ CORREGIDO (Iconos visuales arreglados)
1. **[TEST] Registro:** Crear usuario nuevo. Verificar que no salgan códigos raros en los iconos de éxito/error.
2. **[TEST] Login:** Entrar con el usuario. Verificar redirección rápida.

---

## 🟢 FASE 2: DASHBOARD USUARIO
**Estado:** ✅ CORREGIDO (Error crítico de sintaxis `!=` eliminado)
1. **[TEST] Carga:** Entrar a `/mi-cuenta/`. **Ya no debe salir "TemplateSyntaxError"**.
2. **[TEST] Visual:** Verificar que la barra de progreso de KYC y los textos se vean profesionales (sin `{{ }}` rotos).

---

## 🟡 FASE 3: MOTOR FINANCIERO (CRÉDITOS)
**Estado:** 🛠️ PARCHEADO (Botón MP desbloqueado)
1. **[RE-TEST] Compra MP:** Ir a "Comprar Créditos". Seleccionar paquete. Clic en **Mercado Pago**.
   *   **Resultado Esperado:** Redirección exitosa a Dashboard con mensaje "Pago Simulado Exitoso". (Antes no hacía nada).
2. **[TEST] Compra Crypto:** Probar flujo de "Reportar Pago Crypto" subiendo cualquier hash. Debe quedar en "Pendiente".

---

## 🟢 FASE 4: INVERSIÓN (CORE)
**Estado:** ✅ ESTABLE
1. **[TEST] Invertir:** Usar los créditos simulados para comprar una participación en un proyecto (ej. $100).
2. **[TEST] Resultado:** Verificar descuento de saldo y aparición en "Mis Inversiones".

---

## 🟡 FASE 5: PROYECTOS & DROPS (ESCASEZ)
**Estado:** 🛠️ LOGICA BLINDADA (Límites de Stock)
1. **[RE-TEST CRÍTICO] Overselling:**
   *   Ubica un proyecto con Drop de 1500 tokens (stock real del drop 450 aprox).
   *   Intenta comprar **451** tokens (o más del límite disponible).
   *   **Resultado Esperado:** El sistema debe decir **"Error: Solo quedan X tokens en esta fase"** y BLOQUEAR la compra. (Antes la dejaba pasar).

---

## 🟢 FASE 6: KYC (IDENTIDAD)
**Estado:** ✅ ESTABLE
1. **[TEST] Subida:** Subir documentos en formulario KYC.
2. **[TEST] Admin KYC:** Entrar como Admin, ver la solicitud. Verificar que el nombre de usuario se vea bien en el título (antes salía código roto).

---

## ⚪ FASE 7: DATA ROOM (LEGAL)
**Estado:** ℹ️ PENDIENTE DE REVISIÓN
1. **[TEST RÁPIDO]** Entrar a documento privado -> Debe pedir NDA -> Aceptar NDA -> Ver documento.

---

## ⚪ FASE 8: FUNCIONES PREMIUM (AURORA)
**Estado:** ℹ️ AUTOMÁTICO
1. **[OBSERVACIÓN]** Si eres usuario GOLD/DIAMOND, al invertir verifica si recibes Cashback automático en tu historial.

---

## 🟢 FASE 9: SEGURIDAD (HACKING)
**Estado:** 🛡️ BLINDADO (XSS Username)
1. **[RE-TEST] Inyección:** Registra un usuario con nombre `<h1>HACKER</h1>`.
2. **[TEST] Resultado:** Ve al Admin Panel > Usuarios. El nombre debe verse como texto plano `< h1 >...`, **NO** como un título gigante.

---

## ⚪ FASE 10: SEGURIDAD ADMIN (2FA)
**Estado:** ⏸️ POSPUESTO
*   *Se configurará en producción (requiere instalación de app móvil).*

---

## 🟡 FASE 11: HERRAMIENTAS DE ADMIN
**Estado:** 🛠️ CORREGIDO (Modales y URLs)
1. **[RE-TEST] Cambiar Tier:** Ve a `Admin Panel > Usuarios`. Clic en botón "Estrella" de un usuario.
   *   **Resultado:** El modal abre y el botón "Guardar" FUNCIONA (ya no da Error 404).
2. **[RE-TEST] Ajustar Saldo:** Clic en botón "Cartera" (Azul).
   *   **Resultado:** El modal abre y permite sumar/restar saldo correctamente.

---

### 📝 RESUMEN PARA TI:
Concentra tu energía ahora mismo en:
1.  **Fase 3.1 (MP Button)**: Confirma que ya funciona.
2.  **Fase 5.1 (Drop Limit)**: Confirma que ya NO deja comprar de más.
3.  **Fase 11.1 (Admin Modals)**: Confirma que ya puedes cambiar Tiers y Saldos sin error 404.

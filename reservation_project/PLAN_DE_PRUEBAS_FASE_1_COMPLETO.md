# PLAN DE PRUEBAS FASE 1: BASE DEL NEGOCIO & DROPS
**Objetivo General:** Validar que la infraestructura base del Marketplace (Roles, Proyectos Externos, Drops y RWA) funcione correctamente antes de pasar a la Fase 2 (Pagos Avanzados).

---

## 🟢 A. SEPARACIÓN DE PROYECTOS (Marketplace Core)
**Objetivo:** Verificar que el sistema distingue entre "Proyectos de la Casa" (Internal) y "Proyectos de Terceros" (External).

| ID | Nombre de la Prueba | Pasos a Ejecutar | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **MK-01** | **Proyecto Interno (Admin)** | 1. Entra al Admin Django. <br> 2. Crea un Proyecto con `owner_type = INTERNAL`. | El proyecto debe guardarse y aparecer en el home como "Destacado" o "Oficial". | ✅ |
| **MK-02** | **Proyecto Externo (Wizard)** | 1. Logueate como Fraccionador. <br> 2. Crea un proyecto desde el Dashboard. | El proyecto debe guardarse con `owner_type = EXTERNAL` automáticamente y estado `REVIEW`. | ✅ |
| **MK-03** | **Filtrado Dashboard** | 1. Como Fraccionador, mira "Mis Proyectos". | Solo debes ver TUS proyectos externos, no los de otros ni los internos. | ✅ |

---

## 🟢 B. ROL "FRACCIONADOR" (Fractionalizer)
**Objetivo:** Validar que un usuario externo pueda operar pero con límites (Sandbox).

| ID | Nombre de la Prueba | Pasos a Ejecutar | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **FR-01** | **Acceso Restringido** | 1. Intenta entrar a `/portal/fractionalizer/` sin estar logueado o siendo un usuario normal. | Debe redirigir al Login o mostrar "Acceso Denegado". | ✅ |
| **FR-02** | **Estado KYB (Aprobación)** | 1. Con un usuario nuevo (KYB pendiente), intenta crear proyecto. | Debe bloquear el acceso: "Tu cuenta debe ser aprobada". | ✅ |
| **FR-03** | **Creación Exitosa** | 1. Con usuario KYB Aprovado, completa el formulario de proyecto (con GPS correctos). | Redirige al Dashboard con mensaje de éxito. Proyecto en estado `Review`. | ✅ |
| **FR-04** | **Edición Permitida** | 1. Edita un proyecto propio (cambia descripción). | Se guardan los cambios. | ✅ |
| **FR-05** | **Edición Prohibida** | 1. Intenta editar un proyecto ajeno por URL ID. | Error 403 o redirección al dashboard (No permitido). | ✅ |

---

## 🟢 C. GESTIÓN DE DROPS (Ventanas de Venta)
**Objetivo:** Verificar que el sistema bloquea compras fuera de fecha y controla el stock por Drop.

| ID | Nombre de la Prueba | Pasos a Ejecutar | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **DR-01** | **Crear Drop Futuro** | 1. En Admin, crea un Drop para un proyecto con fecha de inicio "Mañana". <br> 2. Activa `venta_solo_drops = True` en el proyecto. | En el frontend, el botón de compra debe decir "Próximamente" o estar deshabilitado. | ✅ |
| **DR-02** | **Crear Drop Activo** | 1. Crea un Drop con fecha inicio "Ayer" y fin "Mañana". | En el frontend, el botón debe estar **HABILITADO** y mostrar el contador de tiempo restante. | ✅ |
| **DR-03** | **Stock del Drop** | 1. Configura Drop con `tokens_disponibles = 5`. <br> 2. Simula compras de 5 tokens. | Al llegar a 0, el Drop debe cerrarse o mostrar "Sold Out" automáticamente. | ✅ |
| **DR-04** | **Precio Override** | 1. Ponle precio especial al Drop ($50 en vez de $100). | Al ir al checkout, el precio unitario debe ser $50. | ✅ |

---

## 🟢 E. METADATOS RWA (Pre-Blockchain) - **YA PROBADO**
**Objetivo:** Garantizar la integridad de los datos físicos del activo.

| ID | Nombre de la Prueba | Pasos a Ejecutar | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **RW-01** | **Persistencia Error** | Guardar con datos faltantes. | Formulario recarga sin borrar datos. Alerta visible. | ✅ |
| **RW-02** | **Validación GPS** | Guardar con Latitud `-4132` (sin punto). | Error bloqueante: "Latitud fuera de rango". No guarda. | ✅ |
| **RW-03** | **GPS Correcto** | Guardar con Latitud `-41.32`. | Guarda exitosamente. JSON: `{"lat": -41.32}`. | ✅ |
| **RW-04** | **Inmutabilidad (Admin)** | Entrar como Admin a ver proyecto con GPS. | Campos de coordenadas deben ser de solo lectura (si se implementó lógica de readonly). | ⬜ |

---

### 📝 Resumen de Ejecución
- **Total Pruebas:** 16
- **Aprobadas:** 3 (RWA Metadata Críticas)
- **Pendientes:** 13 (Drops, Accesos y Marketplace)

**Instrucciones:** Ejecuta las pruebas pendientes (Punto A, B, C) manual o automáticamente para dar por cerrada la Fase 1.

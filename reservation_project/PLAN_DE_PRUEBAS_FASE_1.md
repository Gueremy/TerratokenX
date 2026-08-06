# Plan de Pruebas - Fase 1: RWA Gateway & Metadata

Este documento detalla los casos de prueba necesarios para validar la finalización de la Fase 1 del proyecto RWA Gateway.
**Objetivo:** Garantizar que los Metadatos RWA (GPS, SPV, Data Room) se capturen, almacenen y protejan correctamente bajo reglas de inmutabilidad simulada (Blockchain-ready).

---

## 🏗️ 1. Pruebas de Creación de Proyecto (Fractionalizer)

**Actor:** Usuario Fraccionador (Fractionalizer)
**Ruta:** `/portal/fractionalizer/create/`

| ID | Caso de Prueba | Pasos | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-01** | **Campos Obligatorios RWA** | 1. Llenar datos básicos.<br>2. Dejar vacíos Latitud, Longitud y SPV.<br>3. Click en "Guardar". | El navegador impide el envío. Muestra mensaje "Completa este campo" en los inputs RWA. | ⬜ |
| **TC-02** | **Formato GPS con Punto (.)** | 1. Ingresar Lat: `-41.32`, Lng: `-72.98`.<br>2. Guardar. | Proyecto creado exitosamente. Los datos se guardan correctamente. | ⬜ |
| **TC-03** | **Formato GPS con Coma (,)** | 1. Ingresar Lat: `-41,32`, Lng: `-72,98`.<br>2. Guardar. | El sistema acepta la coma, la convierte a punto internamente y guarda `-41.32`. No da error. | ⬜ |
| **TC-04** | **Visualización de Advertencia** | 1. Acceder al formulario de creación.<br>2. Ir a tab "Compliance & RWA". | Se muestra el banner naranja de "Atención: Datos Inmutables en Blockchain". | ⬜ |

---

## ✏️ 2. Pruebas de Edición - Proyecto Nuevo (Datos Vacíos)

**Escenario:** El proyecto fue creado antes de esta actualización o se dejaron campos opcionales vacíos (si aplicara).
**Ruta:** `/portal/fractionalizer/edit/<id>/`

| ID | Caso de Prueba | Pasos | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-05** | **Campos Editables si Vacíos** | 1. Abrir un proyecto sin datos GPS/SPV.<br>2. Ir a tab "Compliance". | Los campos Lat, Lng y SPV están habilitados para escribir. Tienen asterisco (*) rojo. | ⬜ |
| **TC-06** | **Guardado de Corrección** | 1. Ingresar datos en los campos vacíos.<br>2. Guardar. | Los datos se guardan. Al recargar la página, los campos aparecen rellenos. | ⬜ |

---

## 🔒 3. Pruebas de Inmutabilidad (Bloqueo)

**Escenario:** El proyecto YA TIENE datos RWA guardados.
**Ruta:** `/portal/fractionalizer/edit/<id>/`

| ID | Caso de Prueba | Pasos | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-07** | **Bloqueo de Edición (Frontend)** | 1. Abrir proyecto con datos RWA.<br>2. Intentar escribir en Lat/Lng/SPV. | Los campos son `readonly`. Tienen estilo visual diferente (opacidad/candado). No permiten escritura. | ⬜ |
| **TC-08** | **Visualización Correcta** | 1. Verificar que los números se vean.<br>2. Verificar formato. | Se ven los números (ej: `-41.32`). No están ocultos ni vacíos. | ⬜ |
| **TC-09** | **Mensaje de Blockchain** | 1. Revisar debajo de los inputs. | Aparece el texto "Registrado en Blockchain" con icono de candado. | ⬜ |

---

## 🛡️ 4. Pruebas de Panel de Administración ("Modo Dios")

**Actor:** Superusuario / Admin
**Ruta:** `/admin-panel/projects/edit/<id>/`

| ID | Caso de Prueba | Pasos | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-10** | **Visualización JSON** | 1. Buscar sección "Metadatos RWA".<br>2. Revisar campo "Datos GPS". | Se muestra el JSON crudo: `{"lat": -41.32, "lng": -72.98}`. | ⬜ |
| **TC-11** | **Bloqueo Admin** | 1. Intentar editar el JSON o el SPV Name.<br>2. Verificar comportamiento. | Los campos están bloqueados (grisáceos/readonly) por el script de seguridad. Aparece candado. | ⬜ |
| **TC-12** | **Banner de Alerta Admin** | 1. Revisar encabezado de sección RWA. | Banner de advertencia presente explicando la inmutabilidad. | ⬜ |

---

## 🛠️ 5. Pruebas de Integridad de Datos (Técnicas)

**Herramienta:** `python manage.py shell` o visualización directa en DB.

| ID | Caso de Prueba | Pasos | Resultado Esperado | Estado |
| :--- | :--- | :--- | :--- | :--- |
| **TC-13** | **Persistencia JSON** | 1. Consultar `Proyecto.objects.get(id=X).gps_data`. | Debe retornar un diccionario `{'lat': float, 'lng': float}` o un string JSON válido. | ⬜ |
| **TC-14** | **Rechazo de Basura** | 1. Intentar enviar texto "HOLA" en latitud (vía burp/postman o script). | El sistema debe rechazarlo o limpiar el input, no guardar "HOLA" en un campo numérico. | ⬜ |

---

**Resultado Final de la Fase 1:**
- [ ] Aprobado
- [ ] Requiere Correcciones

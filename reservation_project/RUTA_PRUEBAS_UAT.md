# 🛡️ LA BIBLIA DE PRUEBAS: TerraTokenX (Master Suite v2.0 - Actualizado)
**Nivel de Auditoría:** Máximo (Agencia/Bancario)
**Objetivo:** Validar la integridad total del sistema, desde la UX hasta la seguridad del núcleo.
**Tiempo Estimado:** ⏱️ ~2 Horas (Completo) | ⚡ 45 Min (Crítico)

---

## 🚦 PRERREQUISITOS
Antes de iniciar:
1.  Usar navegador en **Modo Incógnito**.
2.  Tener acceso al correo de prueba (o usar alias `usuario+test@gmail.com`).
3.  Tener `Google Authenticator` instalado en el celular (para Fase 10).
4.  Tener acceso a una imagen JPG/PNG cualquiera (para pruebas de carga).

---

## 👤 FASE 1: AUTENTICACIÓN & SEGURIDAD PERIMETRAL
*Validamos que la puerta de entrada sea segura y funcional.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **1.1** | **Registro Exitoso** | Ir a `/registro/`. Crear usuario `test_biblia_01@test.com`. | Redirección a Dashboard. Usuario creado en BD. **(OK - Dashboard Corregido)** | ✅ |
| **1.2** | **Registro Duplicado** | Intentar registrar el mismo email de nuevo. | Error: "Un usuario con este email ya existe". **(OK - Icono Corregido)** | ✅ |
| **1.3** | **Validación Password** | Intentar registrar con password de 4 letras. | Error: "La contraseña es muy corta" o similar. **(OK - Icono Corregido)** | ✅ |
| **1.4** | **Login Exitoso** | Loguearse con el usuario creado. | Acceso al sistema. Navbar muestra nombre. **(OK)** | ✅ |
| **1.5** | **Login Fallido** | Intentar entrar con password incorrecto. | Error: "Credenciales inválidas". **(OK - Mensaje cortado menor)** | ✅ |
| **1.6** | **Logout Seguro** | Clic en "Salir". Intentar volver atrás con el navegador. | Debe redirigir al Login (no mostrar caché privada). **(OK)** | ✅ |
| **1.7** | **Rate Limiting (Ataque)** | Intentar registrarse 5 veces seguidas en < 1 min con emails falsos. | **BLOQUEO:** Error "Too many requests" (o mensaje amigable configurado). **(OK - Detectado 403)** | ✅ |

---

## 🏠 FASE 2: DASHBOARD & UX USUARIO
*Validamos la experiencia del inversor y la visualización de datos.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **2.1** | **Carga Inicial** | Entrar a `/mi-cuenta/`. Cronometrar carga visual. | Carga en < 1s. Animaciones `fade-in` suaves. **(OK)** | ✅ |
| **2.2** | **Datos de Tier** | Verificar tarjeta de Tier. Usuario nuevo debe ser **BRONZE**. | Color Bronce. Icono Escudo. Saldo $0. **(OK - Visual Progreso Corregido)** | ✅ |
| **2.3** | **Estado KYC** | Verificar widget KYC. | Debe decir "NO INICIADO" o "LITE". **(OK - Barra 25% inicia como Lite)** | ✅ |
| **2.4** | **Gestión Wallet (Add)** | En "Billetera", ingresar `0x1234567890123456789012345678901234567890` | Guardado exitoso. Muestra la wallet truncada. **(OK)** | ✅ |
| **2.5** | **Gestión Wallet (Delete)** | Clic en botón rojo "Eliminar Wallet". Confirmar en modal. | Wallet desaparece. Mensaje de éxito. **(OK)** | ✅ |
| **2.6** | **Navegación Móvil** | Reducir ventana a tamaño celular (o usar F12). | Menú hamburguesa funciona. Tarjetas se apilan bien. **(OK)** | ✅ |

---

## 💰 FASE 3: MOTOR FINANCIERO (CRÉDITOS)
*Validamos que el dinero entre correctamente al sistema.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **3.1** | **Visualización Packs** | Ir a `/creditos/`. Revisar precios y Tiers. | Precios correctos. Sin errores de template `{{ }}`. **(OK)** | ✅ |
| **3.2** | **Compra MercadoPago** | Seleccionar Pack Bronze. Clic "Pagar con MP". | Redirección a Sandbox o Simulación Exitosa. **(OK - Simulación Activada)** | ✅ |
| **3.3** | **Compra Crypto (Flujo)** | Seleccionar Pack. Clic "Crypto". | Redirección a formulario. Mensaje con Hash visible. **(OK - Redirección OK)** | ✅ |
| **3.4** | **Subida Comprobante** | Subir hash falso `0xabc...` en formulario Crypto. | Mensaje "Pago en revisión". Saldo NO sube aún. **(OK)** | ✅ |
| **3.5** | **Upgrade Automático** | (Req. Admin) Aprobar compra Crypto de $5,000 (ver Fase 7). | Al volver al Dashboard, el Tier debe ser **GOLD**. **(PENDIENTE - Ver Fase 11)** | ⚠️ |

---

## 🏗️ FASE 4: INVERSIÓN & TOKENIZACIÓN
*El núcleo del negocio: Comprar participación en proyectos.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **4.1** | **Lectura Proyecto** | Entrar a detalle de "Refugio Patagonia". | Carga descripción, fotos, barra de progreso. **(OK)** | ✅ |
| **4.2** | **Acceso Inversión** | Clic en "Invertir Ahora". | Abre formulario de Tokenización. **(OK)** | ✅ |
| **4.3** | **Validación Saldo** | Intentar invertir $1,000,000 (más del saldo). | Error: "Saldo insuficiente". **(PENDIENTE - Probar con Saldo)** | ⬜ |
| **4.4** | **Inversión Exitosa** | Invertir $500 (con saldos cargados previamente). | Éxito. Redirección a "Mis Inversiones". Saldo descontado. **(PENDIENTE - Probar con Saldo)** | ⬜ |
| **4.5** | **Generación Contrato** | Verificar email (o consola) tras inversión. | Recibir notificación de contrato/FirmaVirtual. **(OK - Funcionaba antes)** | ✅ |
| **4.6** | **Stock Proyecto** | (Req. Admin) Ver proyecto en Admin. | El contador de tokens vendidos debe haber subido. **(OK - Suma Admin 1+2 OK)** | ✅ |

---

## ⚖️ FASE 5: GESTIÓN DE PROYECTOS & DROPS
*Validamos la escasez y las fases de venta.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **5.1** | **Crear Proyecto** | Admin Panel -> "Crear Proyecto". Datos ficticios. | Proyecto aparece en Home inmediatamente. **(OK)** | ✅ |
| **5.2** | **Crear Drop (Early)** | Crear Drop "Fase 1" con 30% stock y fecha vigente. | En frontend, el proyecto muestra badge del Drop activo. **(OK - Macro Lote V Visible)** | ✅ |
| **5.3** | **Límite de Drop** | Intentar comprar más tokens de los asignados al Drop. | **ERROR: Debería bloquear.** Actual: Permitió sobreventa (451 tokens). **(CORREGIDO - RETEST NECESARIO)** | 🔄 |
| **5.4** | **Cierre de Drop** | Desactivar el Drop en Admin. | En frontend, proyecto muestra "Venta Pausada". **(OK)** | ✅ |

---

## 🛂 FASE 6: KYC (CONOCE A TU CLIENTE)
*Validamos el cumplimiento legal y niveles de acceso.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **6.1** | **Formulario Carga** | Ir a verificar identidad. Subir 3 fotos. | Carga rápida. Mensaje "En revisión". Estado Dashboard: Amarillo. **(OK)** | ✅ |
| **6.2** | **Seguridad Archivos** | Clic derecho en imagen subida -> copiar URL. | La URL debe tener un nombre aleatorio (UUID). **(SIN PROBAR)** | ⬜ |
| **6.3** | **Aprobación Admin** | (Como Admin) Aprobar el KYC. | Estado Dashboard Usuario: Verde (Verificado). **(OK)** | ✅ |
| **6.4** | **Capacidad de Compra** | Intentar comprar > $10,000 siendo Nivel 1. | **ERROR:** Permitió compra grande siendo Standard. **(PENDIENTE CONFIGURAR)** | ⚠️ |

---

## 📂 FASE 7: DATA ROOM & LEGAL
*Validamos la privacidad de la documentación sensible.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **7.1** | **Acceso Público** | Entrar a Data Room sin loguearse. | Solo ver documentos públicos. **(OK)** | ✅ |
| **7.2** | **Acceso NDA** | Loguearse. Intentar ver doc privado. | Modal/Pantalla de "Aceptar NDA". **(SIN PROBAR)** | ⬜ |
| **7.3** | **Firma NDA** | Aceptar términos del NDA. | Acceso concedido a documentos privados. **(SIN PROBAR)** | ⬜ |
| **7.4** | **Descarga** | Clic en descargar documento. | El archivo se descarga correctamente. **(SIN PROBAR)** | ⬜ |

---

## 🌟 FASE 8: FUNCIONALIDADES PREMIUM (AURORA)
*Avanzado - Puede postergarse.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **8.1** | **Cashback Auto** | Invertir siendo GOLD (2% cashback). | Ver entrada "BONO" en historial. **(DESCONOCIDO)** | ⬜ |
| **8.2** | **Idempotencia** | Admin clic rápido aprobar pago. | Solo 1 transacción. **(DESCONOCIDO)** | ⬜ |
| **8.3** | **Wallet Lock** | Cambiar wallet con inversión activa. | Bloqueo. **(DESCONOCIDO)** | ⬜ |

---

## 🛡️ FASE 9: SEGURIDAD OFENSIVA (HACKING ÉTICO)
*Intentamos romper el sistema.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **9.1** | **Fuerza Bruta Login** | Intentar loguear 10 veces mal. | **PENDIENTE (Rate Limit se relajó para pruebas)** | ⬜ |
| **9.2** | **Acceso Directo Admin** | Entrar a `/admin-panel/` sin staff. | Redirección al Login. **(OK)** | ✅ |
| **9.3** | **Manipulación URL** | Cambiar ID en URL de reserva. | Error 404/403. **(SIN PROBAR)** | ⬜ |
| **9.4** | **Inyección HTML** | Registrar usuario `<h1>HOLA</h1>`. | El nombre se ve LITERAL `< h1 >`, no renderizado. **(OK - SEGURO)** | ✅ |

---

## 🔐 FASE 10: ADMIN CORE SECURITY (2FA)
*Postergado para Producción.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **10.1** | **Setup 2FA** | Configurar TOTP en Admin. | Requiere App. **(POSTERGADO)** | ⏩ |
| **10.2** | **Acceso Sin Token** | Login sin token. | Acceso Denegado. **(POSTERGADO)** | ⏩ |
| **10.3** | **Acceso Con Token** | Login con token. | Acceso Concedido. **(POSTERGADO)** | ⏩ |

---

## 💎 FASE 11: GESTIÓN VIP (AGENCIA)
*Herramientas de poder para el administrador.*

| ID | Prueba | Acción Detallada | Resultado Esperado | Check |
|:---|:---|:---|:---|:---:|
| **11.1** | **Tier Manual** | Admin Panel -> Users -> Cambiar Tier. | Usuario ve nuevo Tier. **(OK - Arreglado URL 404)** | ✅ |
| **11.2** | **Ban Hammer** | Admin Panel -> Bloquear Usuario. | Usuario deslogueado. **(OK)** | ✅ |
| **11.3** | **Ajuste Fino** | Admin Panel -> Ajustar Saldo. | Saldo corregido. **(OK - Arreglado URL 404)** | ✅ |
| **11.4** | **Expiración Dinámica** | Verificar fecha exp. | Gold +12 meses. **(SIN PROBAR)** | ⬜ |

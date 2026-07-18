# Sprints y Estado del Proyecto — TerraTokenX

## Estado del QA (última corrida: 2026-04-25, commit fc3e9a9)

```
PASS: 26 (47%)  ✅ funciona
FAIL:  7 (13%)  ❌ existe pero roto — BLOQUEANTES
WARN:  3  (5%)  ⚠️ funciona con advertencia
SKIP: 19 (35%)  ⏳ no implementado aún
```

### FAIL Críticos — resolver en Bloque 0

| ID | Error exacto | Fix |
|----|-------------|-----|
| QA-01-D | FirmaVirtual: 105 referencias en 10 archivos | Eliminar todas las referencias y campos |
| QA-02-C | 5 campos FV en Reserva | Migración destructiva (ver protocolo en seguridad.md) |
| QA-03-B | UNIQUE constraint en slug al crear EXTERNAL | Auto-generar slug con sufijo único |
| QA-06-B | NOT NULL en Coupon.valid_from sin default | Agregar default=timezone.now a valid_from |
| QA-07-C | charmap crash al confirmar Reserva | Fix encoding en signal/hook de email |
| QA-12-H | djangorestframework no instalado | pip install djangorestframework + configurar |
| QA-02-E | UserProfile signal roto (user.userprofile falla) | Fix signal post_save en signals.py |

### WARN — resolver en Bloque 0

| ID | Advertencia | Fix |
|----|------------|-----|
| QA-07-D | Sistema permite bajar Reserva de CONFIRMADO a PENDIENTE | Agregar validación en model.save() |
| QA-09-D | Webhook MP no registrado en URLs | Agregar path en booking/urls.py |
| QA-09-B | Tokens MP son de producción real (APP_USR-...) | Usar tokens de TEST en entorno local |

---

## Progreso por semana

Marcar ✅ cuando la tarea esté completa Y verificada con sus criterios de aceptación.
Esta tabla es la "memoria" del proyecto entre sesiones de Claude Code.

---

## BLOQUE 0 — Deuda Técnica (Semana 1)

**Gate de salida:** 0 FAIL + 0 WARN en QA antes de tocar Fase 1.

| Tarea | Responsable | Estado |
|-------|-------------|--------|
| Eliminar FirmaVirtual de 10 archivos | Gueremy | ⏳ |
| Eliminar 5 campos FV de Reserva + migración | Gueremy | ⏳ |
| Fix encoding bug (charmap en email/hook) | Gueremy | ⏳ |
| Fix slug duplicado en Proyecto EXTERNAL | Gueremy | ⏳ |
| Fix Coupon valid_from NOT NULL | Gueremy | ⏳ |
| pip install djangorestframework + configurar | Gueremy | ⏳ |
| Fix UserProfile signal (post_save) | Gueremy | ⏳ |
| Crear grupos Fractionalizer y JoanAdmin en DB | Gueremy | ⏳ |
| Registrar webhook MP en urls.py | Gueremy | ⏳ |
| Proteger transición CONFIRMADO → PENDIENTE | Gueremy | ⏳ |
| Correr QA completo → meta: 0 FAIL / 0 WARN | Gueremy | ⏳ |

**Criterios de aceptación Bloque 0:**
```
✅ PASS si:
  - python manage.py check → "System check identified no issues (0 silenced)"
  - grep -r "firmavirtual" --include="*.py" → 0 resultados
  - grep -r "FirmaVirtual" --include="*.py" → 0 resultados
  - from booking.models import Reserva; r = Reserva(); print(dir(r)) → sin campos FV
  - Crear Proyecto EXTERNAL con nombre repetido → slug único (con sufijo)
  - Crear Coupon sin valid_from → se asigna timezone.now() automáticamente
  - import rest_framework → sin ImportError
  - User.objects.first().userprofile → no lanza RelatedObjectDoesNotExist
  - Grupo 'Fractionalizer' existe: Group.objects.filter(name='Fractionalizer').exists() == True

❌ NO AVANZA A FASE 1 si:
  - Cualquiera de los anteriores falla
```

---

## FASE 1 — Backend Completo (Semanas 2-6)

**Gate de salida:** Flujo de compra end-to-end con las 3 pasarelas + créditos. 0 errores en QA-01 a QA-13.

---

### Semana 2 — Modelos nuevos + excepciones + selectors

**Docs a leer:** `core/modelos.md`, `negocio/drops.md`, `negocio/creditos-tiers.md`

| Tarea | Estado |
|-------|--------|
| Crear `CreditBalance` model | ⏳ |
| Crear `CreditTransaction` model | ⏳ |
| Crear `TierConfig` model + fixtures (4 tiers) | ⏳ |
| Crear `FeeConfig` model + fixtures (5 tipos) | ⏳ |
| Crear `AuditLog` model | ⏳ |
| Crear `FraccionadorProfile` model | ⏳ |
| Migraciones de todos los modelos nuevos | ⏳ |
| `booking/exceptions.py` con 5 excepciones | ⏳ |
| `booking/selectors.py` → `get_drop_activo()` | ⏳ |

**Criterios Semana 2:**
```
✅ PASS si:
  - python manage.py migrate → sin errores
  - CreditBalance.objects.create(user=u, ...) → funciona
  - TierConfig.objects.filter(tier=1).first().nombre == 'Bronze'
  - FeeConfig.objects.filter(tipo='LISTING').first().porcentaje == Decimal('1.5')
  - get_drop_activo(proyecto_sin_drop) → None
  - get_drop_activo(proyecto_con_drop_activo) → ProjectDrop instance
  - from booking.exceptions import DropInactivo → sin ImportError
```

---

### Semana 3 — Services core + KYC Middleware

**Docs a leer:** `negocio/drops.md §services`, `negocio/kyc.md`, `infra/auth.md`

| Tarea | Estado |
|-------|--------|
| `validar_compra()` en services.py | ⏳ |
| `crear_reserva_pendiente()` con select_for_update | ⏳ |
| `confirmar_reserva()` con atomic + AuditLog | ⏳ |
| `KYCCheckMiddleware` registrado en settings | ⏳ |
| Constante `KYC_LIMITS_USD` con 4 tiers en constants.py | ⏳ |
| Tests unitarios: validar_compra(), confirmar_reserva() | ⏳ |
| Test race condition: dos compras simultáneas del último token | ⏳ |

**Criterios Semana 3:**
```
✅ PASS si:
  - validar_compra() lanza DropInactivo si no hay drop activo
  - validar_compra() lanza StockInsuficiente si cantidad > stock
  - validar_compra() lanza LimiteKYCSuperado si supera límite de tier
  - confirmar_reserva() es idempotente (segunda llamada → IdempotenciaError)
  - Middleware bloquea POST /api/v1/comprar/ para user T1 con total >= $1.000
  - Middleware NO bloquea GET requests
  - Test race condition: solo 1 de 2 threads tiene éxito con stock=1
```

---

### Semana 4 — Créditos RWA + Fee Schedule

**Docs a leer:** `negocio/creditos-tiers.md`, `core/sql-performance.md §atomic`

| Tarea | Estado |
|-------|--------|
| `calcular_fee()` con Decimal — 0 floats | ⏳ |
| `calcular_precio_creditos()` por tier | ⏳ |
| `comprar_creditos()` service | ⏳ |
| `acreditar_creditos()` post-pago | ⏳ |
| `aplicar_credito_en_checkout()` | ⏳ |
| Task `expirar_creditos_vencidos` en Celery | ⏳ |
| Beat schedule 2 AM en settings | ⏳ |
| Vista admin para gestionar créditos y fees | ⏳ |

**Criterios Semana 4:**
```
✅ PASS si:
  - calcular_fee(Decimal('1000'), 'LISTING', 1) == Decimal('15.00')  # 1.5% con 7.5% descuento T1
  - calcular_precio_creditos(Decimal('1000'), 4) == Decimal('600.00')  # 40% off T4
  - aplicar_credito_en_checkout con monto > balance → CreditoInsuficiente
  - balance no puede quedar negativo después de aplicar crédito
  - Test: expirar_creditos_vencidos() expira balances con expires_at < now()
```

---

### Semana 5 — Integración Cryptomus

**Docs a leer:** `negocio/pagos.md §cryptomus`, `apis/didit.md §wallet-screening`
**⚙️ Credenciales necesarias:** CRYPTOMUS_MERCHANT_ID, CRYPTOMUS_PAYMENT_API_KEY

| Tarea | Estado |
|-------|--------|
| `booking/integrations/cryptomus.py` | ⏳ |
| Crear invoice desde Django | ⏳ |
| Webhook handler con verificación MD5 | ⏳ |
| Manejo de TODOS los statuses (paid, paid_over, wrong_amount, cancel, check, fail) | ⏳ |
| Idempotencia con cryptomus_uuid único | ⏳ |
| Variables CRYPTOMUS_* en settings | ⏳ |
| Tests: firma válida, firma inválida, webhook duplicado | ⏳ |
| Test con webhook de prueba de Cryptomus (endpoint /test-webhook/) | ⏳ |

**Criterios Semana 5:**
```
✅ PASS si:
  - POST /api/webhooks/cryptomus/ con firma válida + status=paid → Reserva CONFIRMADO
  - POST /api/webhooks/cryptomus/ con firma inválida → 403
  - Segundo POST con mismo uuid → 200 sin cambios
  - status=wrong_amount → Reserva FALLIDO + stock devuelto al Drop
  - status=cancel → stock devuelto al Drop
  - is_final=false → 200 sin procesar
```

---

### Semana 6 — Kushki + API REST completa

**Docs a leer:** `negocio/pagos.md §kushki`, `infra/api-rest.md`
**⚙️ Credenciales necesarias:** KUSHKI_PUBLIC_KEY, KUSHKI_PRIVATE_KEY

| Tarea | Estado |
|-------|--------|
| `booking/integrations/kushki.py` | ⏳ |
| Webhook Kushki con validación | ⏳ |
| Variables KUSHKI_* en settings | ⏳ |
| 10+ endpoints REST documentados | ⏳ |
| Serializers para todos los endpoints | ⏳ |
| Colección Postman o Bruno exportada | ⏳ |

**Criterios Semana 6 — HITO 2:**
```
✅ HITO 2 ($1.000.000 CLP) SE COBRA si:
  - Flujo completo MP: crear reserva → pago → webhook → CONFIRMADO
  - Flujo completo Cryptomus: invoice → webhook → CONFIRMADO
  - Flujo completo Kushki: tokenizar → cobrar → CONFIRMADO
  - Créditos: comprar con descuento de tier → usar en checkout → saldo descontado
  - KYC Middleware bloqueando correctamente por tier
  - 10+ endpoints responden con auth correcta
  - 0 FAIL en QA completo
  - Colección Postman compartida con Dev Asociado
```

---

## FASE 2 — Frontend React (Semanas 7-11)

Esta fase es principalmente del Dev Asociado. Gueremy provee endpoints y soporte.
Detalle completo en v2 del documento (se genera al llegar a semana 7).

**Gate de salida:** UAT aprobado por Joan. Flujo end-to-end completo.

---

## FASE 3 — Blockchain Polygon (Semanas 12-16)

Detalle completo en `docs/blockchain.md` (se genera en v3, semana 12).

**Gate de salida:** Token real emitido en Polygon Mainnet. Joan lo ve en Polygonscan.
Nota: Gas MATIC para deploy y operaciones es a cargo de Joan Sandoval (cláusula del contrato).

---

## Regla de comunicación con Joan

Cada viernes, mensaje de 3 líneas:
1. Qué se hizo esta semana
2. Qué sigue la próxima semana
3. Si hay algo que Joan necesita resolver o decidir

# TerraTokenX Backend — CLAUDE.md

Plataforma RWA de tokenización de terrenos en la Patagonia chilena.
Stack: Django 5.2.3 + DRF + PostgreSQL en Render.
Solo backend. Frontend lo hace Dev Asociado (React + Vite, repo separado).

---

## REGLAS NO NEGOCIABLES

1. **Dinero → SIEMPRE `Decimal`. NUNCA `float`.** Un centavo mal redondeado en finanzas es un bug crítico.
2. **FirmaVirtual NO EXISTE.** 0 referencias en todo el código. Si encuentras una, es un bug que debes reportar antes de continuar.
3. **El sistema tiene 4 tiers: Bronze / Silver / Gold / Black.** Nunca 3. Nunca 5.
4. **Lógica de negocio → `services.py`. NUNCA en views.** Las views solo reciben input, llaman un service, devuelven output.
5. **Stock de Drops y saldo de Créditos → SIEMPRE `select_for_update()` + `@transaction.atomic`.** Sin esto hay race conditions que permiten sobreventa.
6. **Webhooks → SIEMPRE verificar firma + idempotencia ANTES de procesar.** Primero verifica, después actúa.
7. **Lenguaje financiero → PROHIBIDO usar:** `rentabilidad`, `dividendo`, `retorno garantizado`, `plusvalía`. En código, comentarios, emails y mensajes de error.
8. **Secrets → NUNCA hardcodear.** Todo en variables de entorno. Nunca en código, nunca en commits.
9. **Migraciones destructivas → primero backup de la tabla, después migrar.** Especialmente Bloque 0 (eliminar campos FirmaVirtual de Reserva).
10. **Un cambio a la vez.** Anunciar, hacer, verificar, reportar. Si falla → `git checkout -- <archivo>` antes de continuar.

---

## CICLO OBLIGATORIO POR CADA CAMBIO

```
1. ANUNCIAR   → "Voy a cambiar X porque Y"
2. HACER      → el cambio mínimo necesario
3. VERIFICAR  → python manage.py check  (debe decir 0 issues)
               → correr el test específico de esa tarea
4. REPORTAR   → ✅ o ❌ con detalle
5. Si ❌      → git checkout -- <archivo>  ANTES de cualquier otro cambio
```

---

## ANTES DE INTEGRAR CUALQUIER API

```
⚠️  STOP. Antes de escribir código de integración:

1. Decirle a Gueremy qué credenciales necesito (están documentadas
   en docs/apis/<nombre-api>.md sección "Credenciales requeridas")
2. ESPERAR confirmación con los valores reales
3. Verificar que las variables están en .env y en settings/local.py
4. Solo entonces escribir el código de integración

NUNCA inventar API keys, merchant IDs ni endpoints.
```

---

## ESTADO ACTUAL DEL PROYECTO

```
QA última corrida: 2026-04-25
PASS: 26 | FAIL: 7 | WARN: 3 | SKIP: 19

BLOQUEANTES (no avanzar a Fase 1 hasta resolverlos):
  ❌ FirmaVirtual: 105 referencias en 10 archivos
  ❌ Encoding bug: charmap crash al confirmar Reserva
  ❌ Slug duplicado: UNIQUE constraint en Proyecto EXTERNAL
  ❌ Coupon valid_from: NOT NULL sin default
  ❌ DRF no instalado: djangorestframework faltante
  ❌ UserProfile signal roto
  ❌ Webhook MP no registrado en URLs
  ⚠️  Grupo Fractionalizer no existe en DB

REGLA: 0 FAIL + 0 WARN antes de tocar Fase 1.
```

---

## DÓNDE ESTÁ TODO

| Necesito saber sobre... | Leer... |
|------------------------|---------|
| Estructura de carpetas y capas | `docs/core/arquitectura.md` |
| Modelos y campos de DB | `docs/core/modelos.md` |
| Queries rápidas y SQL | `docs/core/sql-performance.md` |
| Variables de entorno | `docs/core/entornos.md` |
| Seguridad y vulnerabilidades | `docs/core/seguridad.md` |
| Sistema de Drops | `docs/negocio/drops.md` |
| Créditos y Tiers | `docs/negocio/creditos-tiers.md` |
| KYC por tier | `docs/negocio/kyc.md` |
| Pasarelas de pago | `docs/negocio/pagos.md` |
| Auth y permisos | `docs/infra/auth.md` |
| Endpoints REST | `docs/infra/api-rest.md` |
| Redis y Celery | `docs/infra/redis-celery.md` |
| Archivos y storage | `docs/infra/storage-r2.md` |
| Testing | `docs/infra/testing.md` |
| API Didit (KYC) | `docs/apis/didit.md` |
| API Floid (Registro Civil) | `docs/apis/floid.md` |
| API Resend (email) | `docs/apis/resend.md` |
| Legal y compliance Chile | `docs/legal-compliance.md` |
| Sprint actual y criterios | `docs/sprints.md` |
| Qué NO tocar en MVP | `DIFERIDO.md` |

---

## INICIO DE SESIÓN

Al empezar cada sesión nueva de trabajo, leer `docs/sprints.md` y decir:
- En qué semana estamos
- Qué tarea está en progreso
- Cuál es el próximo paso concreto

# TerraTokenX — Índice Maestro

Antes de empezar cualquier tarea, buscar la semana en la tabla de abajo
y leer los docs indicados. No adivinar — la respuesta siempre está en los docs.

---

## Tabla Sprint → Documentos

| Semana | Qué se hace | Leer antes de empezar |
|--------|-------------|----------------------|
| **Bloque 0** | Eliminar deuda técnica | `core/arquitectura.md` · `core/modelos.md` · `core/seguridad.md` · `sprints.md §B0` |
| **Semana 2** | Modelos nuevos + excepciones + selectors | `core/modelos.md` · `negocio/drops.md` · `negocio/creditos-tiers.md` |
| **Semana 3** | Services core + KYC Middleware | `negocio/drops.md` · `negocio/kyc.md` · `core/sql-performance.md` · `infra/auth.md` |
| **Semana 4** | Créditos RWA + Fee Schedule | `negocio/creditos-tiers.md` · `core/sql-performance.md` · `infra/redis-celery.md` |
| **Semana 5** | Integración Cryptomus | `negocio/pagos.md` · `apis/didit.md` (wallet screening) · `infra/redis-celery.md` |
| **Semana 6** | Integración Kushki + API REST completa | `negocio/pagos.md` · `infra/api-rest.md` · `infra/testing.md` |
| **Sem 7-11** | Frontend (Fase 2) | Ver docs/sprints.md §F2 — pendiente v2 |
| **Sem 12-16** | Blockchain (Fase 3) | `blockchain.md` — pendiente v3 |

---

## Mapa completo de archivos

```
CLAUDE.md                    ← Reglas, ciclo de trabajo, estado actual
.env.example                 ← Todas las variables de entorno

docs/
│
├── 00-INDEX.md              ← Este archivo
│
├── core/
│   ├── arquitectura.md      ← Capas, carpetas, Service/Selector pattern
│   ├── modelos.md           ← Todos los modelos con campos, soft delete, índices
│   ├── sql-performance.md   ← select_related, atomic, select_for_update, índices
│   ├── entornos.md          ← settings/, env vars, secretos, deploy checklist
│   └── seguridad.md         ← OWASP para TTX, race conditions, guardrails agente
│
├── negocio/
│   ├── drops.md             ← ProjectDrop, selectors, services, excepciones, 30/30/40
│   ├── creditos-tiers.md    ← 4 tiers, compra/uso de créditos, fees, expiración
│   ├── kyc.md               ← KYCCheckMiddleware, KYC_LIMITS_USD, Didit flow
│   └── pagos.md             ← MP + Cryptomus + Kushki, statuses, idempotencia
│
├── apis/
│   ├── didit.md             ← KYC / AML / Wallet Screening (con bloque credenciales)
│   ├── floid.md             ← Registro Civil Chile (con bloque credenciales)
│   └── resend.md            ← Email transaccional (con bloque credenciales)
│
├── infra/
│   ├── auth.md              ← JWT simplejwt, permisos DRF, rate limiting
│   ├── api-rest.md          ← Versionado, serializers, endpoints Fase 1
│   ├── redis-celery.md      ← Caché, Celery tasks, Beat schedule, expiración créditos
│   ├── storage-r2.md        ← Cloudflare R2, django-storages, por qué no Render
│   └── testing.md           ← pytest, factories, mocks de APIs, tests de race condition
│
├── legal-compliance.md      ← Ley 21.719, AML, claims prohibidos, soft delete
├── sprints.md               ← Estado QA actual + 16 semanas + criterios de aceptación
└── blockchain.md            ← [PENDIENTE v3] web3.py, ERC-3643, mint, Metamask

DIFERIDO.md                  ← WebSockets, Circuit Breaker, Feature Flags — NO en MVP
```

---

## Convenciones de iconos en los docs

```
✅  Implementado y funcionando
❌  Existe pero está roto
⏳  Pendiente de implementar
🚧  En progreso
⚠️  Atención especial requerida
🔴  Crítico — bloqueante
🟡  Importante — no bloqueante
🟢  Opcional para MVP
```

---

## Regla de oro del índice

Si una tarea no aparece en la tabla de arriba, preguntarle a Gueremy
antes de asumir qué doc leer. No improvisar el contexto.

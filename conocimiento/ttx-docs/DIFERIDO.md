# DIFERIDO.md — No tocar en MVP

Este archivo lista funcionalidades que NO se implementan en las primeras 11 semanas.
Son buenas ideas, pero si se implementan ahora queman presupuesto y tiempo
que se necesita para terminar el flujo de pago y los paneles.

**Regla:** Si Claude Code sugiere implementar algo de esta lista antes de la Fase 2,
responder: "Está en DIFERIDO.md — no ahora."

---

## WebSockets (Django Channels)

**Por qué se difiere:** Agrega complejidad real al deploy en Render (proceso ASGI separado),
requiere Redis channel layers configurado, y aumenta el costo mensual.

**Lo que hace ahora en su lugar:**
El frontend puede hacer polling HTTP cada 10-15 segundos para actualizar el stock del Drop
y la barra de progreso. Es suficiente para el MVP y no requiere infraestructura extra.

**Cuándo implementar:** Fase 2+ cuando haya feedback real de Joan y usuarios.

---

## Circuit Breaker para servicios externos

**Por qué se difiere:** Para 2 developers part-time con < 50 usuarios activos,
la probabilidad de que Cryptomus o Kushki fallen y afecten a múltiples usuarios
simultáneamente es muy baja. El costo de implementación supera el beneficio en MVP.

**Lo que hace ahora en su lugar:**
Los Celery tasks tienen retry automático (3-5 intentos con backoff).
Si una pasarela falla, el task reintenta. Si falla 5 veces, queda en DLQ para revisión manual.

**Cuándo implementar:** Cuando haya volumen real (Fase 3+).

---

## Feature Flags (django-waffle)

**Por qué se difiere:** Para MVP, las variables de entorno hacen el 80% del trabajo:
`CRYPTOMUS_ENABLED=True` en settings activa/desactiva Cryptomus sin deploy.
`TIER_4_INVITE_ONLY=True` desactiva T4 para usuarios generales.

**Lo que hace ahora en su lugar:**
Variables de entorno booleanas en settings. Joan puede pedir a Gueremy cambiarlas.

**Cuándo implementar:** Cuando Joan necesite controlar features sin contactar a Gueremy.

---

## i18n / Internacionalización completa

**Por qué se difiere:** El mercado inicial es Chile/LatAm en español.
La expansión global (inglés, portugués) es Fase 4+.

**Lo que hace ahora:**
`LANGUAGE_CODE = 'es-cl'` en settings. Todos los strings en español.
Los emails se envían en español. Las excepciones tienen mensajes en español.

**Cuándo implementar:** Cuando haya usuarios activos fuera de LatAm.

---

## Communication Center (fraccionador → holders)

**Por qué se difiere:** No hay holders en el MVP (aún no hay tokens emitidos).
La funcionalidad de enviar updates a holders es para Fase 3+ cuando existan tokens reales.

**Cuándo implementar:** Después del Go-Live blockchain (semana 16+).

---

## Modelo completo de FraccionadorProfile (retiros, distribuciones)

**Por qué se difiere:** El modelo base se crea en Semana 2.
Pero los retiros y las distribuciones voluntarias a holders son operaciones
que requieren que haya dinero real en la plataforma y holders reales.

**Cuándo implementar:** Fase 2, semana 9 (panel fraccionador).

---

## Twilio SMS (verificación T1 Bronze por SMS)

**Por qué se difiere:** T1 Bronze puede verificar solo con email en el MVP.
El SMS agrega $0.05 por verificación y complejidad de integración que no es crítica.

**Cuándo implementar:** Cuando haya evidencia de fraude o necesidad de SMS real.

---

## Polygonscan API (dashboard on-chain)

**Por qué se difiere:** Solo aplica en Fase 3 cuando haya tokens reales.

---

## CoinGecko API y Frankfurter (conversión de precios)

**Por qué se difiere:** El marketplace en Fase 1 muestra precios en USD.
La conversión a CLP es nice-to-have para el MVP del frontend.

**Cuándo implementar:** Fase 2, semana 7 (marketplace React).

---

## OpenAPI / Swagger (drf-spectacular)

**Por qué se difiere:** Para Fase 1, una colección Postman es suficiente para el Dev Asociado.
drf-spectacular es útil pero no crítico para las primeras 11 semanas.

**Cuándo implementar:** Antes de Fase 2, para que Dev Asociado tenga docs auto-generadas.

---

## Backups automatizados a R2

**Por qué se difiere:** Render PostgreSQL tiene backups diarios en planes pagos.
El backup manual a R2 es una capa extra que se implementa antes del Go-Live.

**Cuándo implementar:** Semana 15 (antes del deploy a Mainnet).

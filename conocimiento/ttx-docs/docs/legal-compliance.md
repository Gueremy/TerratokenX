# Legal y Compliance — TerraTokenX

## Posición del equipo de desarrollo

El equipo (Gueremy + Dev Asociado) es **proveedor técnico de software únicamente**.
No es responsable del modelo de negocio, decisiones comerciales, ni resultados financieros.
La responsabilidad regulatoria y legal de TerraTokenX es de Joan Sandoval (cláusula 5 y 6 del contrato).

---

## Ley 21.719 — Protección de datos personales Chile (activa diciembre 2026)

### Qué aplica a TerraTokenX

Los datos de KYC (cédula, selfie, dirección, RUT) son datos sensibles bajo la Ley 21.719.

**Obligaciones técnicas del sistema:**

1. **Consentimiento explícito** al registrarse (checkbox en frontend — trabajo de Dev Asociado)
2. **Derecho al olvido** — el usuario puede pedir borrar sus datos personales
3. **Datos financieros NO se borran** (obligación fiscal y auditoría)
4. **Transferencias internacionales** → Didit y Floid deben operar en jurisdicciones adecuadas (lo cumplen)

### Implementación del derecho al olvido

```python
# booking/services.py

def anonimizar_usuario(user_id: int, motivo: str) -> None:
    """
    Anonimiza datos personales SIN borrar historial financiero.
    Cumple Ley 21.719 sin comprometer integridad de auditoría.
    """
    from django.contrib.auth.models import User

    with transaction.atomic():
        user = User.objects.get(id=user_id)
        perfil = user.userprofile

        # Anonimizar datos personales
        user.first_name = ''
        user.last_name  = ''
        user.email      = f'anonimizado_{user_id}@deleted.terratokenx.com'
        user.set_unusable_password()
        user.save()

        # Anonimizar perfil KYC — pero mantener tier (para auditoría)
        perfil.wallet_address    = ''
        perfil.didit_session_id  = ''
        perfil.kyc_verificado_en = None
        perfil.save()

        # CONSERVAR: Reservas, CreditTransactions, AuditLog
        # Son obligación fiscal y de compliance. No se borran.

        AuditLog.registrar(
            accion='usuario.anonimizado',
            objeto=user,
            datos_despues={'motivo': motivo, 'user_id': user_id},
        )
```

---

## AML — Lavado de dinero

### Qué hace la plataforma

1. **Cryptomus** verifica AML en wallets que hacen payouts (automático en su API)
2. **Didit** hace AML screening en T3 Gold y T4 Black (via KYC flow)
3. **Floid** valida identidad contra Registro Civil (para chilenos)

### Reporte a UAF (Unidad de Análisis Financiero)

Las transacciones cash > $10.000 USD deben reportarse a la UAF según Ley 19.913.
Esto es responsabilidad de Joan, no del sistema. El sistema provee el `AuditLog` con los datos necesarios.

### Umbral técnico de alerta

```python
# Si una compra supera este monto, generar alerta en AuditLog
UMBRAL_ALERTA_UAF_USD = Decimal('10000.00')

# En services.py, al confirmar reserva:
if reserva.total >= UMBRAL_ALERTA_UAF_USD:
    AuditLog.registrar(
        accion='alerta.uaf.umbral',
        objeto=reserva,
        datos_despues={
            'monto': str(reserva.total),
            'user_id': reserva.user_id,
            'nota': 'Transacción supera umbral UAF $10.000 USD',
        },
    )
```

---

## Claims permitidos y prohibidos

### El equipo de desarrollo NUNCA escribe esto:

```python
# ❌ PROHIBIDO — en código, comentarios, emails, mensajes de error, UI:
"rentabilidad"
"dividendo"
"retorno garantizado"
"retorno de inversión"
"plusvalía garantizada"
"respaldo directo por tierras"
"garantía de recompra"
"rendimiento"  # en contexto financiero
```

### El equipo puede escribir esto:

```python
# ✅ PERMITIDO:
"Acceso a proyectos RWA verificados"
"Créditos para compras dentro de TerraTokenX"
"Ventanas de acceso limitadas"
"Descuento según tu nivel de membresía"
"Proyectos verificados y documentados"
```

---

## Soft delete — datos financieros

**NUNCA borrar físicamente:**
- `Reserva` (historial de transacciones)
- `CreditTransaction` (registro de créditos)
- `AuditLog` (inmutable por diseño — sin delete ni update)
- `FraccionadorProfile` (para auditoría post-cierre de cuenta)

Todos estos modelos heredan de `SoftDeleteModel` o son inmutables por diseño.

---

## Responsabilidad de contratos inteligentes (Fase 3)

El equipo despliega y opera los contratos ERC-3643 como infraestructura técnica.
La responsabilidad legal de los tokens como instrumentos financieros, su registro ante la CMF,
y su clasificación regulatoria recae exclusivamente en Joan Sandoval.
El equipo no ofrece asesoría legal ni asume responsabilidad regulatoria.

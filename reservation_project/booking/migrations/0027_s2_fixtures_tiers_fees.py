from decimal import Decimal

from django.db import migrations
from django.db.models import Sum


TIERS = [
    # (tier, nombre, cap, desc_fees, desc_creditos, kyc)
    (1, 'Bronze', Decimal('1000.00'), Decimal('7.50'), Decimal('10.00'), 'lite'),
    (2, 'Silver', Decimal('5000.00'), Decimal('15.00'), Decimal('20.00'), 'standard'),
    (3, 'Gold', Decimal('15000.00'), Decimal('22.50'), Decimal('30.00'), 'standard'),
    (4, 'Black VIP', Decimal('25000.00'), Decimal('31.50'), Decimal('40.00'), 'edd'),
]

FEES = [
    # (tipo, porcentaje, minimo, descripcion)
    ('LISTING', Decimal('1.50'), Decimal('500.00'), 'Listing/Originación de proyecto'),
    ('TRANSACCION', Decimal('1.00'), Decimal('0.00'), 'Fee de transacción por compra'),
    ('ADMIN', Decimal('1.00'), Decimal('0.00'), 'Administración anual prorrateada'),
    ('CASHOUT', Decimal('1.00'), Decimal('0.00'), 'Retiro/Cash-out'),
    ('PREMIUM', Decimal('0.00'), Decimal('10.00'), 'Servicios premium'),
]


def cargar_fixtures(apps, schema_editor):
    TierConfig = apps.get_model('booking', 'TierConfig')
    FeeConfig = apps.get_model('booking', 'FeeConfig')

    for tier, nombre, cap, desc_fees, desc_creditos, kyc in TIERS:
        TierConfig.objects.update_or_create(
            tier=tier,
            defaults={
                'nombre': nombre,
                'cap_creditos_usd': cap,
                'descuento_fees_pct': desc_fees,
                'descuento_creditos_pct': desc_creditos,
                'kyc_requerido': kyc,
            },
        )

    for tipo, pct, minimo, descripcion in FEES:
        FeeConfig.objects.update_or_create(
            tipo=tipo,
            defaults={
                'porcentaje': pct,
                'monto_minimo_usd': minimo,
                'descripcion': descripcion,
                'activo': True,
            },
        )


def borrar_fixtures(apps, schema_editor):
    apps.get_model('booking', 'TierConfig').objects.all().delete()
    apps.get_model('booking', 'FeeConfig').objects.all().delete()


def sync_tokens_vendidos_inicial(apps, schema_editor):
    """Materializa tokens_vendidos desde las reservas confirmadas existentes."""
    Proyecto = apps.get_model('booking', 'Proyecto')
    Reserva = apps.get_model('booking', 'Reserva')
    for proyecto in Proyecto.objects.all():
        vendidos = Reserva.objects.filter(
            proyecto=proyecto, estado_pago='CONFIRMADO'
        ).aggregate(total=Sum('cantidad_tokens'))['total'] or 0
        Proyecto.objects.filter(pk=proyecto.pk).update(tokens_vendidos=vendidos)


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0026_s2_soft_delete'),
    ]

    operations = [
        migrations.RunPython(cargar_fixtures, borrar_fixtures),
        migrations.RunPython(sync_tokens_vendidos_inicial, migrations.RunPython.noop),
    ]

from django.db import migrations


def crear_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.get_or_create(name='Fractionalizer')
    Group.objects.get_or_create(name='JoanAdmin')


def eliminar_grupos(apps, schema_editor):
    Group = apps.get_model('auth', 'Group')
    Group.objects.filter(name__in=['Fractionalizer', 'JoanAdmin']).delete()


def crear_perfiles_faltantes(apps, schema_editor):
    User = apps.get_model('auth', 'User')
    UserProfile = apps.get_model('booking', 'UserProfile')
    for user in User.objects.filter(profile__isnull=True):
        UserProfile.objects.create(user=user)


class Migration(migrations.Migration):

    dependencies = [
        ('booking', '0023_fixes_b0_slug_coupon_pasarelas'),
        ('auth', '0012_alter_user_first_name_max_length'),
    ]

    operations = [
        migrations.RunPython(crear_grupos, eliminar_grupos),
        migrations.RunPython(crear_perfiles_faltantes, migrations.RunPython.noop),
    ]

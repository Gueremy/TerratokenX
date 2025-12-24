from django.shortcuts import render, redirect, get_object_or_404
from django.http import HttpResponse, JsonResponse
from django.contrib.auth import authenticate, login, logout
from django.contrib.auth.forms import AuthenticationForm
from .forms import ReservaForm
from .models import Reserva, DiaFeriado, Coupon, Configuracion
from django.contrib import messages
from django.core.mail import send_mail
from django.template.loader import render_to_string
from django.conf import settings
from django.db.models import Count
from datetime import datetime, timedelta, date
import os
from django.contrib.admin.views.decorators import staff_member_required
import json
import openpyxl
from reportlab.pdfgen import canvas
from reportlab.lib.pagesizes import letter
from reportlab.lib.units import inch
from reportlab.platypus import SimpleDocTemplate, Table, TableStyle, Paragraph
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from urllib.parse import urlencode
from django.urls import reverse
from django.views.decorators.csrf import csrf_exempt
from django.db import transaction # Import transaction module
from google.oauth2 import service_account
from googleapiclient.discovery import build
import mercadopago
import logging


# Obtener una instancia del logger para registrar errores de forma más detallada
logger = logging.getLogger(__name__)

def create_google_calendar_link(reserva):
    """Genera un enlace para agregar la reserva al Calendario de Google."""
    # Desactivado para tokens
    return "#"

def add_event_to_spa_calendar(reserva):
    """
    Agrega un evento al calendario central del negocio usando una cuenta de servicio.
    """
    # Desactivado para tokens
    pass

def login_view(request):
    if request.user.is_authenticated and request.user.is_staff:
        return redirect('admin_panel')

    if request.method == 'POST':
        form = AuthenticationForm(request, data=request.POST)
        if form.is_valid():
            username = form.cleaned_data.get('username')
            password = form.cleaned_data.get('password')
            user = authenticate(username=username, password=password)
            if user is not None and user.is_staff:
                login(request, user)
                return redirect('admin_panel')
            else:
                messages.error(request, "Acceso denegado. Solo para administradores.")
        else:
            messages.error(request, "Nombre de usuario o contraseña inválidos.")
    else:
        form = AuthenticationForm()
    return render(request, 'booking/login.html', {'form': form})

def logout_view(request):
    logout(request)
    return redirect('reservation_form')

def create_mp_preference(request, reserva_id):
    """
    Crea una preferencia de pago en Mercado Pago (Checkout Pro) y redirige al usuario.
    """
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if reserva.pagado:
        messages.info(request, "Esta reserva ya ha sido pagada.")
        return redirect('reservation_success', reserva_id=reserva.id)

    sdk = mercadopago.SDK(settings.MERCADO_PAGO_ACCESS_TOKEN)

    # Define las URLs a las que Mercado Pago redirigirá al usuario.
    # `build_absolute_uri` es crucial para que funcione en producción.
    back_urls = {
        "success": request.build_absolute_uri(reverse('reservation_success', args=[reserva.id])),
        "failure": request.build_absolute_uri(reverse('reservation_form')), # Vuelve al formulario si falla
        "pending": request.build_absolute_uri(reverse('reservation_success', args=[reserva.id])), # También a éxito, pero con estado pendiente
    }

    preference_data = {
        "items": [
            {
                "title": f"Reserva Inversión TerraTokenX - {reserva.numero_reserva}",
                "quantity": 1,
                "unit_price": float(reserva.total),
                "currency_id": "CLP", # ¡IMPORTANTE! Asegúrate de que esta es tu moneda. Usa "ARS", "MXN", etc.
            }
        ],
        "payer": {
            "name": reserva.nombre,
            "email": reserva.correo,
        },
        "back_urls": back_urls,
        "auto_return": "approved", # Redirige automáticamente solo si el pago es aprobado
        "external_reference": str(reserva.id), # ID de tu reserva para identificarla después
    }

    try:
        preference_response = sdk.preference().create(preference_data)
        preference = preference_response["response"]
        # Redirigir al usuario a la URL de pago de Mercado Pago
        return redirect(preference["init_point"])
    except Exception as e:
        # Mensaje amigable para el administrador/cliente
        logger.error(f"Error Mercado Pago: {e}")
        messages.error(request, "Error de Configuración: La API Key de Mercado Pago parece haber expirado o es inválida. Revise sus credenciales.")
        return redirect('reservation_form')

def _get_filtered_reservas(request):
    """
    Función auxiliar para obtener un queryset de reservas filtrado
    basado en los parámetros GET o POST.
    """
    if request.method == 'POST' and 'selected_ids' in request.POST:
        selected_ids = request.POST.getlist('selected_ids')
        if not selected_ids:
            return Reserva.objects.none() # Devuelve un queryset vacío si no hay IDs
        return Reserva.objects.filter(id__in=selected_ids).order_by('-fecha')
    
    # Filtros para GET
    reservas = Reserva.objects.all()
    pagado = request.GET.get('pagado')

    if pagado in ['true', 'false']: reservas = reservas.filter(pagado=(pagado == 'true'))
    
    return reservas.order_by('-created_at')

@staff_member_required
def admin_panel(request):
    # --- Lógica para actualizar la configuración de precios ---
    if request.method == 'POST' and 'update_prices' in request.POST:
        config = Configuracion.load()
        # Usar .get() y limpiar el valor para evitar errores (ej: "35.000")
        precio_base_token_str = ''.join(filter(str.isdigit, request.POST.get('precio_base_token', '')))

        if precio_base_token_str:
            try:
                config.precio_base_token = int(precio_base_token_str)
                config.save()
                messages.success(request, "Precio del Token actualizado correctamente.")
            except (ValueError, TypeError):
                messages.error(request, "Por favor, ingresa un valor numérico válido.")
        else:
            messages.error(request, "El campo de precio es requerido.")
        
        # Redirigir a la misma página para prevenir reenvío del formulario
        return redirect('admin_panel')

    try:
        reservas = _get_filtered_reservas(request)
        dias_feriados = DiaFeriado.objects.all().order_by('fecha')
        coupons = Coupon.objects.all().order_by('-valid_to')
        config = Configuracion.load()  # Cargar configuración para mostrarla
        return render(request, 'booking/admin_panel.html', {
            'reservas': reservas,
            'dias_feriados': dias_feriados,
            'coupons': coupons,
            'config': config,  # Pasar el objeto de configuración a la plantilla
            'request': request,
        })
    except Exception as e:
        return HttpResponse(f"Error en admin_panel: {e}", status=500)

@staff_member_required
def editar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        form = ReservaForm(request.POST, instance=reserva)
        if form.is_valid():
            form.save()
            return redirect('admin_panel')
    else:
        form = ReservaForm(instance=reserva)
    return render(request, 'booking/editar_reserva.html', {'form': form, 'reserva': reserva})

@staff_member_required
def eliminar_reserva(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    if request.method == 'POST':
        reserva.delete()
        return redirect('admin_panel')
    return render(request, 'booking/eliminar_reserva.html', {'reserva': reserva})

def reservation_form(request):
    print("DEBUG: CARGANDO VISTA reservation_form (Debería usar v2)")
    if request.method == 'POST':
        form = ReservaForm(request.POST)
        if form.is_valid():
            # Assign the validated coupon object to the instance before saving
            if 'coupon_code' in form.cleaned_data and form.cleaned_data['coupon_code']:
                form.instance.coupon = form.cleaned_data['coupon_code']

            # Capturar método de pago
            metodo_pago = request.POST.get('metodo_pago', 'MP')
            reserva = form.save(commit=False)
            reserva.metodo_pago = metodo_pago
            reserva.save()
            
            # Enviar correo de "Reserva Pendiente"
            # Enviar correo de "Reserva Pendiente" (Diferenciado por método de pago)
            if reserva.metodo_pago == 'CRYPTO':
                subject = '⏳ Instrucciones para finalizar tu inversión en TerraTokenX'
                template_name = 'booking/email/pending_reservation_crypto.html'
            else:
                # Default to Mercado Pago msg
                subject = 'Tu solicitud de reserva está pendiente de pago'
                template_name = 'booking/email/pending_reservation_mp.html'

            context = {
                'reserva': reserva,
            }

            html_message = render_to_string(template_name, context)

            try:
                send_mail(
                    subject,
                    '', # El mensaje de texto plano
                    from_email=settings.DEFAULT_FROM_EMAIL,
                    recipient_list=[reserva.correo],
                    fail_silently=False,
                    html_message=html_message,
                )
            except Exception as e:
                print(f"Error enviando correo: {e}")

            # Redirección condicional según método de pago
            if reserva.metodo_pago == 'CRYPTO':
                return crear_orden_cryptomarket(reserva)
            else:
                # Default to Mercado Pago
                return redirect('create_mp_preference', reserva_id=reserva.id)
        # Si el formulario no es válido, se renderizará de nuevo con los errores.
    else:
        form = ReservaForm()

    # --- Contexto para la validación del lado del cliente (JavaScript) ---
    config = Configuracion.load()

    return render(request, 'booking/reservation_form_v2.html', {
        'form': form,
        'config': config,
        'precio_base_token': config.precio_base_token,
    })


def reservation_success(request, reserva_id):
    reserva = get_object_or_404(Reserva, id=reserva_id)
    
    payment_status = request.GET.get('status')
    pago_procesado_ahora = False
    
    # Se procesa el pago solo una vez para evitar duplicados si el usuario recarga la página.
    if payment_status == 'approved' and not reserva.pagado:
        # 1. Actualiza la base de datos de forma atómica y segura.
        with transaction.atomic():
            # Recargamos la reserva dentro de la transacción para evitar race conditions.
            reserva_a_pagar = Reserva.objects.select_for_update().get(id=reserva_id)
            if not reserva_a_pagar.pagado:
                reserva_a_pagar.pagado = True
                reserva_a_pagar.save()
                pago_procesado_ahora = True

    # 2. Si el pago se procesó en esta visita, ejecuta las acciones externas (email, calendario).
    if pago_procesado_ahora:
        google_calendar_link_email = create_google_calendar_link(reserva)
        
        # Enviar correo de confirmación
        subject_confirm = '✅ Confirmación: Tu cupo en la Preventa TerraTokenX está asegurado'
        context_confirm = {
            'reserva': reserva,
            'google_calendar_link': google_calendar_link_email,
        }
        html_message_confirm = render_to_string('booking/email/reservation_confirmation.html', context_confirm)
        send_mail(
            subject_confirm, '',
            from_email=settings.DEFAULT_FROM_EMAIL,
            recipient_list=[reserva.correo],
            fail_silently=False,
            html_message=html_message_confirm
        )
        
        # Agregar evento al calendario del negocio
        add_event_to_spa_calendar(reserva)

    # Crear el enlace de Google Calendar para mostrarlo en la página de éxito
    google_calendar_link = create_google_calendar_link(reserva)

    context = {
        'reserva': reserva,
        'payment_status': payment_status,
        'google_calendar_link': google_calendar_link,
    }
    return render(request, 'booking/reservation_success.html', context)


@staff_member_required
def agregar_feriado(request):
    if request.method == 'POST':
        fecha = request.POST.get('fecha')
        descripcion = request.POST.get('descripcion', '')
        if fecha:
            DiaFeriado.objects.get_or_create(fecha=fecha, defaults={'descripcion': descripcion})
    return redirect('admin_panel')

@staff_member_required
def eliminar_feriado(request, feriado_id):
    if request.method == 'POST':
        DiaFeriado.objects.filter(id=feriado_id).delete()
    return redirect('admin_panel')

@staff_member_required
def agregar_cupon(request):
    if request.method == 'POST':
        code = request.POST.get('code')
        discount_percentage = request.POST.get('discount_percentage')
        valid_from = request.POST.get('valid_from')
        valid_to = request.POST.get('valid_to')

        if code and discount_percentage and valid_from and valid_to:
            try:
                Coupon.objects.create(
                    code=code,
                    discount_percentage=int(discount_percentage),
                    valid_from=valid_from,
                    valid_to=valid_to
                )
            except Exception as e:
                messages.error(request, f"Error al agregar cupón: {e}")
    return redirect('admin_panel')

@staff_member_required
def eliminar_cupon(request, coupon_id):
    if request.method == 'POST':
        Coupon.objects.filter(id=coupon_id).delete()
    return redirect('admin_panel')



@staff_member_required
def export_reservas_excel(request):
    """
    Genera un archivo Excel con las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    reservas = _get_filtered_reservas(request)
    if not reservas.exists() and request.method == 'POST':
        messages.error(request, "No seleccionaste ninguna reserva para exportar.")
        return redirect('admin_panel')
    
    # Crear un libro de trabajo y una hoja
    workbook = openpyxl.Workbook()
    sheet = workbook.active
    sheet.title = 'Reservas'

    # Escribir la cabecera
    headers = ['N° Reserva', 'Nombre Cliente', 'Fecha Compra', 'Tokens', 'Total', 'Pagado', 'Correo', 'Teléfono']
    sheet.append(headers)

    # Escribir los datos de cada reserva
    for reserva in reservas:
        sheet.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.created_at.replace(tzinfo=None), # Excel no soporta tz-aware datetime a veces
            reserva.cantidad_tokens,
            reserva.total,
            'Sí' if reserva.pagado else 'No',
            reserva.correo,
            reserva.telefono,
        ])

    # Crear la respuesta HTTP
    response = HttpResponse(content_type='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet')
    response['Content-Disposition'] = 'attachment; filename=reservas.xlsx'
    workbook.save(response)
    
    return response

@staff_member_required
def export_reservas_pdf(request):
    """
    Genera un archivo PDF con una tabla de las reservas.
    - Si es POST, exporta las reservas seleccionadas.
    - Si es GET, exporta las reservas filtradas.
    """
    reservas = _get_filtered_reservas(request)
    if not reservas.exists() and request.method == 'POST':
        messages.error(request, "No seleccionaste ninguna reserva para exportar.")
        return redirect('admin_panel')

    response = HttpResponse(content_type='application/pdf')
    response['Content-Disposition'] = 'attachment; filename="reservas.pdf"'

    doc = SimpleDocTemplate(response, pagesize=letter)
    elements = []
    styles = getSampleStyleSheet()

    # Título del documento
    title = Paragraph("Reporte de Reservas", styles['h1'])
    elements.append(title)

    # Datos para la tabla
    data = [['N° Reserva', 'Cliente', 'Fecha', 'Total', 'Pagado']]
    for reserva in reservas:
        data.append([
            reserva.numero_reserva,
            reserva.nombre,
            reserva.created_at.strftime('%d-%m-%Y'),
            f"${reserva.total:,.0f}".replace(",", "."),
            'Sí' if reserva.pagado else 'No'
        ])

    # Crear y estilizar la tabla
    table = Table(data, colWidths=[1.2*inch, 2*inch, 1.2*inch, 1.2*inch, 0.8*inch])
    style = TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.grey),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 12),
        ('BACKGROUND', (0, 1), (-1, -1), colors.beige),
        ('GRID', (0, 0), (-1, -1), 1, colors.black)
    ])
    table.setStyle(style)
    elements.append(table)

    doc.build(elements)
    return response

def crear_orden_cryptomarket(reserva):
    """
    Placeholder para la integración con CryptoMarket.
    Por ahora retorna una respuesta simulada o redirige a una página de 'Pendiente'.
    """
    # En un futuro:
    # 1. Preparar payload para API CryptoMarket
    # 2. Hacer POST a /api/3/payment/orders
    # 3. Obtener payment_url de la respuesta
    # 4. Redirigir al usuario a esa URL

    # Simulación de respuesta exitosa o redirección temporal
    # Redirigimos a success con status='crypto_pending' para diferenciar.
    # Usamos resolve_url o string con params, pero redirect acepta kwargs para la url, no query params directos.
    # Así que construimos la url primero.
    from django.shortcuts import resolve_url
    
    url = resolve_url('reservation_success', reserva_id=reserva.id)
    return redirect(f'{url}?status=crypto_pending')

def preview_email(request):
    """
    Vista temporal para previsualizar el correo de confirmación.
    """
    class DummyReserva:
        nombre = "Juan Pérez"
        total = 1000000
        numero_reserva = "ORD-2024-001"
        def get_metodo_pago_display(self):
            return "Mercado Pago"
    
    reserva = DummyReserva()
    
    return render(request, 'booking/email/reservation_confirmation.html', {'reserva': reserva})


from django.http import JsonResponse
import json

def validate_coupon(request):
    """
    Validates a coupon code via AJAX.
    """
    if request.method == 'POST':
        try:
            data = json.loads(request.body)
            code = data.get('code', '').strip()
            
            try:
                coupon = Coupon.objects.get(code=code)
                if coupon.is_valid():
                    return JsonResponse({
                        'valid': True,
                        'discount_percentage': coupon.discount_percentage,
                        'message': f'¡Cupón válido! {coupon.discount_percentage}% de descuento aplicado.'
                    })
                else:
                    return JsonResponse({
                        'valid': False,
                        'message': 'El cupón ha expirado o no está activo.'
                    })
            except Coupon.DoesNotExist:
                return JsonResponse({
                    'valid': False,
                    'message': 'Código de cupón no encontrado.'
                })
        except Exception as e:
            return JsonResponse({'valid': False, 'message': 'Error procesando la solicitud.'}, status=400)
    
    return JsonResponse({'valid': False, 'message': 'Método no permitido.'}, status=405)

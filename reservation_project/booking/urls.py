from django.urls import path
from . import views

urlpatterns = [
    path('', views.reservation_form, name='reservation_form'),
    path('success/<int:reserva_id>/', views.reservation_success, name='reservation_success'),
    path('create-preference/<int:reserva_id>/', views.create_mp_preference, name='create_mp_preference'),
    
    # Admin Panel & Auth
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Actions (Estas son las rutas que faltaban)
    path('editar-reserva/<int:reserva_id>/', views.editar_reserva, name='editar_reserva'),
    path('eliminar-reserva/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    path('agregar-feriado/', views.agregar_feriado, name='agregar_feriado'),
    path('eliminar-feriado/<int:feriado_id>/', views.eliminar_feriado, name='eliminar_feriado'),
    path('agregar-cupon/', views.agregar_cupon, name='agregar_cupon'),
    path('eliminar-cupon/<int:coupon_id>/', views.eliminar_cupon, name='eliminar_cupon'),
    path('export-reservas-excel/', views.export_reservas_excel, name='export_reservas_excel'),
    path('export-reservas-pdf/', views.export_reservas_pdf, name='export_reservas_pdf'),
    
    # Preview Email
    path('preview-email/', views.preview_email, name='preview_email'),
    
    # AJAX Coupon Validation
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    
    # Crypto Payment Flow (DIY)
    path('payment/crypto/<int:reserva_id>/', views.payment_crypto_view, name='payment_crypto_view'),
    path('api/crypto/get-details/', views.api_get_crypto_details, name='api_get_crypto_details'),
    path('api/crypto/check-payment/', views.api_check_payment_status, name='api_check_payment_status'),
    path('api/crypto/manual-confirm/', views.api_manual_confirm_payment, name='api_manual_confirm_payment'),

    # Crypto Payment Simulation (Development Only)
    path('simulate-crypto-payment/<int:reserva_id>/', views.simulate_crypto_payment, name='simulate_crypto_payment'),
]

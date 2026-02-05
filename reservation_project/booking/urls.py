from django.urls import path
from django.contrib.auth import views as auth_views
from . import views
# Force reload

urlpatterns = [
    path('', views.landing_page, name='landing'),
    path('buy/', views.reservation_form, name='reservation_form'),
    path('success/<int:reserva_id>/', views.reservation_success, name='reservation_success'),
    path('create-preference/<int:reserva_id>/', views.create_mp_preference, name='create_mp_preference'),
    
    # Admin Panel & Auth
    path('admin-panel/', views.admin_panel, name='admin_panel'),
    path('admin-panel/dashboard/', views.admin_dashboard, name='admin_dashboard'),
    path('admin-panel/sales/', views.admin_sales, name='admin_sales'),
    path('admin-panel/signatures/', views.admin_signatures, name='admin_signatures'),
    path('login/', views.login_view, name='login'),
    path('logout/', views.logout_view, name='logout'),

    # Admin Users Management
    path('admin-panel/users/', views.admin_users, name='admin_users'),
    path('admin-panel/users/edit/<int:user_id>/', views.admin_edit_user, name='admin_edit_user'),
    path('admin-panel/users/block/<int:user_id>/', views.admin_block_user, name='admin_block_user'),
    path('admin-panel/kyc/', views.admin_kyc_list, name='admin_kyc_list'),
    path('admin-panel/kyc/process/<int:profile_id>/', views.admin_kyc_process, name='admin_kyc_process'),

    # Admin Actions (Estas son las rutas que faltaban)
    path('editar-reserva/<int:reserva_id>/', views.editar_reserva, name='editar_reserva'),
    path('eliminar-reserva/<int:reserva_id>/', views.eliminar_reserva, name='eliminar_reserva'),
    path('agregar-feriado/', views.agregar_feriado, name='agregar_feriado'),
    path('eliminar-feriado/<int:feriado_id>/', views.eliminar_feriado, name='eliminar_feriado'),
    path('agregar-cupon/', views.agregar_cupon, name='agregar_cupon'),
    path('eliminar-cupon/<int:coupon_id>/', views.eliminar_cupon, name='eliminar_cupon'),
    path('export-reservas-excel/', views.export_reservas_excel, name='export_reservas_excel'),
    path('export-reservas-pdf/', views.export_reservas_pdf, name='export_reservas_pdf'),
    path('reenviar-contrato/<int:reserva_id>/', views.reenviar_contrato, name='reenviar_contrato'),
    
    # Preview Email
    path('preview-email/', views.preview_email, name='preview_email'),

    # Project Management
    path('admin-panel/projects/', views.admin_projects, name='admin_projects'),
    path('admin-panel/projects/create/', views.admin_project_create, name='project_create'),
    path('admin-panel/projects/edit/<int:project_id>/', views.admin_project_edit, name='project_edit'),
    path('admin-panel/projects/delete/<int:project_id>/', views.admin_project_delete, name='project_delete'),
    
    # Project Sections CRUD
    path('admin-panel/projects/<int:project_id>/sections/create/', views.admin_section_create, name='section_create'),
    path('admin-panel/sections/edit/<int:section_id>/', views.admin_section_edit, name='section_edit'),
    path('admin-panel/sections/delete/<int:section_id>/', views.admin_section_delete, name='section_delete'),
    
    # Project Documents CRUD (Data Room)
    path('admin-panel/projects/<int:project_id>/documentos/agregar/', views.admin_documento_create, name='documento_create'),
    path('admin-panel/documentos/eliminar/<int:doc_id>/', views.admin_documento_delete, name='documento_delete'),
    
    # Coupon Management (ERP)
    path('admin-panel/coupons/', views.admin_coupons, name='admin_coupons'),
    path('admin-panel/coupons/create/', views.admin_coupon_create, name='admin_coupon_create'),
    path('admin-panel/coupons/edit/<int:coupon_id>/', views.admin_coupon_edit, name='admin_coupon_edit'),
    path('admin-panel/coupons/delete/<int:coupon_id>/', views.admin_coupon_delete, name='admin_coupon_delete'),

    
    # AJAX Coupon Validation
    path('validate-coupon/', views.validate_coupon, name='validate_coupon'),
    
    # Crypto Payment Flow (DIY)
    path('payment/crypto/<int:reserva_id>/', views.payment_crypto_view, name='payment_crypto_view'),
    path('api/crypto/get-details/', views.api_get_crypto_details, name='api_get_crypto_details'),
    path('api/crypto/check-payment/', views.api_check_payment_status, name='api_check_payment_status'),
    path('api/crypto/manual-confirm/', views.api_manual_confirm_payment, name='api_manual_confirm_payment'),

    # Crypto Payment Simulation (Development Only)
    path('simulate-crypto-payment/<int:reserva_id>/', views.simulate_crypto_payment, name='simulate_crypto_payment'),
    
    # Public API for Landing Page Progress Bar
    path('api/stats/', views.api_stats, name='api_stats'),
    path('api/config/', views.api_config, name='api_config'),
    path('api/projects/', views.api_project_list, name='api_project_list'), # Catálogo
    path('api/project-detail/', views.api_project_detail, name='api_project_detail'), # Detalle dinámico
    
    # FirmaVirtual Webhook
    path('api/webhooks/firmavirtual/', views.firmavirtual_webhook, name='firmavirtual_webhook'),
    path('api/firmavirtual/status/<int:reserva_id>/', views.firmavirtual_status, name='firmavirtual_status'),
    
    # Investor Portal
    path('portal/login/', views.investor_login, name='investor_login'),
    path('portal/register/', views.investor_register, name='investor_register'),
    path('dashboard/', views.investor_dashboard, name='investor_dashboard'),
    path('portal/profile/', views.investor_profile, name='investor_profile'),
    path('portal/kyc/', views.investor_kyc, name='investor_kyc'),

    # Password Reset
    path('password-reset/', auth_views.PasswordResetView.as_view(
        template_name='booking/investor/password_reset_form.html',
        email_template_name='booking/investor/password_reset_email.html',
        subject_template_name='booking/investor/password_reset_subject.txt'
    ), name='password_reset'),
    path('password-reset/done/', auth_views.PasswordResetDoneView.as_view(template_name='booking/investor/password_reset_done.html'), name='password_reset_done'),
    path('password-reset-confirm/<uidb64>/<token>/', auth_views.PasswordResetConfirmView.as_view(template_name='booking/investor/password_reset_confirm.html'), name='password_reset_confirm'),
    path('password-reset-complete/', auth_views.PasswordResetCompleteView.as_view(template_name='booking/investor/password_reset_complete.html'), name='password_reset_complete'),
    
    # Protected Catalog using Django (Moved from Hostinger index2.html)
    path('projects/', views.investor_catalog, name='investor_catalog'),
    path('projects/<slug:slug>/', views.investor_project_detail, name='investor_project_detail'),
]

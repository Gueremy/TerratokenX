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
]

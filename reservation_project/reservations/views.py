from django.shortcuts import render, redirect
from django.http import HttpResponse
from .forms import ReservationForm
from .models import Reservation
from django.core.mail import send_mail
from django.conf import settings
from django.utils import timezone

def reservation_form(request):
    if request.method == 'POST':
        form = ReservationForm(request.POST)
        if form.is_valid():
            reservation = form.save(commit=False)
            reservation.status = 'Pending'
            reservation.save()
            
            # Send confirmation email to client
            send_mail(
                'Reservation Confirmation',
                f'Thank you for your reservation, {reservation.name}.',
                settings.DEFAULT_FROM_EMAIL,
                [reservation.email],
                fail_silently=False,
            )
            
            # Send notification email to admin
            send_mail(
                'New Reservation',
                f'A new reservation has been made by {reservation.name}.',
                settings.DEFAULT_FROM_EMAIL,
                [settings.ADMIN_EMAIL],
                fail_silently=False,
            )
            
            return redirect('reservation_success')
    else:
        form = ReservationForm()
    
    return render(request, 'reservations/reservation_form.html', {'form': form})

def reservation_success(request):
    return render(request, 'reservations/reservation_success.html')

def admin_dashboard(request):
    reservations = Reservation.objects.all()
    return render(request, 'reservations/admin_dashboard.html', {'reservations': reservations})
from django.contrib import admin
from .models import Reservation

@admin.register(Reservation)
class ReservationAdmin(admin.ModelAdmin):
    list_display = ('name', 'email', 'phone', 'address', 'date', 'time', 'status')
    search_fields = ('name', 'email', 'phone', 'address')
    list_filter = ('date', 'status')
    ordering = ('-date',)
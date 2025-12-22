from django import forms
from .models import Reservation
from django.core.exceptions import ValidationError
from django.utils import timezone

class ReservationForm(forms.ModelForm):
    class Meta:
        model = Reservation
        fields = ['name', 'email', 'phone', 'address', 'date', 'time']
        widgets = {
            'date': forms.DateInput(attrs={'type': 'date'}),
            'time': forms.TimeInput(attrs={'type': 'time'}),
        }

    def clean_date(self):
        date = self.cleaned_data.get('date')
        if date < timezone.now().date():
            raise ValidationError("The reservation date cannot be in the past.")
        return date

    def clean_time(self):
        time = self.cleaned_data.get('time')
        date = self.cleaned_data.get('date')
        if date and time:
            reservation_datetime = timezone.datetime.combine(date, time)
            if reservation_datetime < timezone.now():
                raise ValidationError("The reservation time cannot be in the past.")
        return time

    def clean(self):
        cleaned_data = super().clean()
        date = cleaned_data.get('date')
        time = cleaned_data.get('time')

        if date and time:
            if Reservation.objects.filter(date=date, time=time).exists():
                raise ValidationError("This time slot is already booked. Please choose another time.")
        
        return cleaned_data
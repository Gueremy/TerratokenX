from django.test import TestCase
from .models import Reservation
from django.urls import reverse
from datetime import datetime, timedelta

class ReservationModelTest(TestCase):
    def setUp(self):
        self.reservation = Reservation.objects.create(
            name="John Doe",
            email="john@example.com",
            phone="1234567890",
            address="123 Main St",
            date=datetime.now().date() + timedelta(days=1),
            time="12:00"
        )

    def test_reservation_creation(self):
        self.assertEqual(self.reservation.name, "John Doe")
        self.assertEqual(self.reservation.email, "john@example.com")
        self.assertEqual(self.reservation.phone, "1234567890")
        self.assertEqual(self.reservation.address, "123 Main St")
        self.assertEqual(self.reservation.date, datetime.now().date() + timedelta(days=1))
        self.assertEqual(self.reservation.time, "12:00")

class ReservationFormTest(TestCase):
    def test_reservation_form_valid(self):
        response = self.client.post(reverse('reservation_form'), {
            'name': 'Jane Doe',
            'email': 'jane@example.com',
            'phone': '0987654321',
            'address': '456 Elm St',
            'date': (datetime.now() + timedelta(days=1)).date(),
            'time': '14:00'
        })
        self.assertEqual(response.status_code, 302)  # Redirect on success

    def test_reservation_form_invalid(self):
        response = self.client.post(reverse('reservation_form'), {
            'name': '',
            'email': 'invalid-email',
            'phone': 'not-a-phone',
            'address': '',
            'date': '',
            'time': ''
        })
        self.assertEqual(response.status_code, 200)  # Stay on the form page
        self.assertFormError(response, 'form', 'name', 'This field is required.')
        self.assertFormError(response, 'form', 'email', 'Enter a valid email address.')

class ReservationAvailabilityTest(TestCase):
    def setUp(self):
        self.reservation = Reservation.objects.create(
            name="Alice Smith",
            email="alice@example.com",
            phone="1231231234",
            address="789 Maple St",
            date=datetime.now().date() + timedelta(days=1),
            time="15:00"
        )

    def test_double_booking(self):
        response = self.client.post(reverse('reservation_form'), {
            'name': 'Bob Brown',
            'email': 'bob@example.com',
            'phone': '3213214321',
            'address': '321 Oak St',
            'date': self.reservation.date,
            'time': self.reservation.time
        })
        self.assertFormError(response, 'form', None, 'This time slot is already booked.')
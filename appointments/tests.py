from datetime import timedelta
from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from appointments.models import Appointment


class AppointmentsFrontendTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.doctor = User.objects.create_user(
            username='dr.house',
            password='Password123!',
            role=User.Role.DOCTOR,
            first_name='Gregory',
            last_name='House'
        )
        self.patient = User.objects.create_user(
            username='pat.wilson',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='James',
            last_name='Wilson'
        )
        self.future_time = timezone.now() + timedelta(days=2)
        self.appointment = Appointment.objects.create(
            patient=self.patient,
            doctor=self.doctor,
            datetime=self.future_time,
            status=Appointment.Status.SCHEDULED,
            reason='Routine clinical follow-up.'
        )

    def test_patient_can_book_appointment(self):
        """Patient can schedule a consultation with a doctor"""
        self.client.login(username='pat.wilson', password='Password123!')
        book_time = (timezone.now() + timedelta(days=4)).strftime('%Y-%m-%dT%H:%M')

        response = self.client.post(reverse('book-appointment'), {
            'doctor': self.doctor.id,
            'datetime': book_time,
            'reason': 'Experiencing mild dizziness during evenings.'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(Appointment.objects.filter(patient=self.patient).count(), 2)
        new_appt = Appointment.objects.filter(reason__contains='dizziness').first()
        self.assertIsNotNone(new_appt)
        self.assertEqual(new_appt.doctor, self.doctor)

    def test_doctor_can_complete_appointment(self):
        """Doctor can mark consultation completed"""
        self.client.login(username='dr.house', password='Password123!')
        response = self.client.post(reverse('update-appointment-status', kwargs={'appointment_id': self.appointment.id}), {
            'status': Appointment.Status.COMPLETED
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.COMPLETED)

    def test_patient_can_cancel_appointment(self):
        """Patient can cancel scheduled consultation"""
        self.client.login(username='pat.wilson', password='Password123!')
        response = self.client.post(reverse('update-appointment-status', kwargs={'appointment_id': self.appointment.id}), {
            'status': Appointment.Status.CANCELLED
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.appointment.refresh_from_db()
        self.assertEqual(self.appointment.status, Appointment.Status.CANCELLED)

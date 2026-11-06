from django.test import TestCase, Client
from django.urls import reverse
from django.utils import timezone
from accounts.models import User
from patients.models import PatientProfile, ClinicalNote
from devices.models import Device
from monitoring.models import VitalReading, Alert, AlertRule
from appointments.models import Appointment


class PatientAndDoctorFrontendTests(TestCase):
    def setUp(self):
        self.client = Client()

        # Doctor
        self.doctor = User.objects.create_user(
            username='dr.smith',
            password='Password123!',
            role=User.Role.DOCTOR,
            first_name='Sarah',
            last_name='Smith'
        )

        # Patient
        self.patient = User.objects.create_user(
            username='pat.alice',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='Alice',
            last_name='Wonder'
        )
        self.profile = PatientProfile.objects.create(
            user=self.patient,
            age=45,
            gender='female',
            blood_group='A+',
            medical_history='Mild Hypertension',
            assigned_doctor=self.doctor,
            emergency_contact='Bob (555-0101)'
        )

        # Another patient not assigned to Dr. Smith
        self.other_patient = User.objects.create_user(
            username='pat.other',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='Other',
            last_name='Person'
        )
        self.other_profile = PatientProfile.objects.create(
            user=self.other_patient,
            age=30,
            gender='male',
            assigned_doctor=None
        )

        # Device
        self.device = Device.objects.create(
            device_id='TEST-POX-01',
            device_type=Device.DeviceType.PULSE_OXIMETER,
            patient=self.patient,
            model_name='PulsePro 2000'
        )

        # Readings
        self.reading_hr = VitalReading.objects.create(
            device=self.device,
            patient=self.patient,
            vital_type='heart_rate',
            value=115.0,
            unit='bpm',
            timestamp=timezone.now()
        )
        self.reading_spo2 = VitalReading.objects.create(
            device=self.device,
            patient=self.patient,
            vital_type='spo2',
            value=96.0,
            unit='%',
            timestamp=timezone.now()
        )

        # Alert Rule & Alert
        self.rule = AlertRule.objects.create(
            vital_type='heart_rate',
            max_value=100.0,
            severity='high',
            description='Tachycardia warning'
        )
        self.alert = Alert.objects.create(
            reading=self.reading_hr,
            rule=self.rule,
            status='open'
        )

    def test_doctor_dashboard_view(self):
        """Doctor dashboard displays assigned patient and open alerts with severity badges"""
        self.client.login(username='dr.smith', password='Password123!')
        response = self.client.get(reverse('doctor-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Wonder")
        self.assertContains(response, "Mild Hypertension")
        self.assertContains(response, "Tachycardia warning")
        self.assertContains(response, "HIGH")
        self.assertContains(response, "Resolve")

    def test_doctor_can_resolve_alert(self):
        """Doctor can triage and mark an alert as resolved"""
        self.client.login(username='dr.smith', password='Password123!')
        response = self.client.post(reverse('resolve-alert', kwargs={'alert_id': self.alert.id}), {
            'resolution_notes': 'Advised rest and fluid intake.'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'resolved')
        self.assertEqual(self.alert.resolved_by, self.doctor)
        self.assertEqual(self.alert.resolution_notes, 'Advised rest and fluid intake.')

    def test_patient_detail_view(self):
        """Patient detail page displays demographics, vital indicators, notes, appointments"""
        self.client.login(username='dr.smith', password='Password123!')
        response = self.client.get(reverse('patient-detail', kwargs={'patient_id': self.patient.id}))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Alice Wonder")
        self.assertContains(response, "TEST-POX-01")
        self.assertContains(response, "Live Telemetry")
        self.assertContains(response, "Heart Rate Telemetry")
        self.assertContains(response, "Oxygen Saturation")
        self.assertContains(response, "Blood Pressure Dynamics")

    def test_patient_can_add_clinical_note(self):
        """Doctor can author clinical notes for patient"""
        self.client.login(username='dr.smith', password='Password123!')
        response = self.client.post(reverse('add-clinical-note', kwargs={'patient_id': self.patient.id}), {
            'note': 'Patient shows good response to lifestyle intervention.'
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertEqual(ClinicalNote.objects.filter(patient=self.patient).count(), 1)
        note = ClinicalNote.objects.first()
        self.assertEqual(note.doctor, self.doctor)
        self.assertIn("lifestyle intervention", note.note)

    def test_patient_dashboard(self):
        """Patient can access personal dashboard with vitals and appointments"""
        self.client.login(username='pat.alice', password='Password123!')
        response = self.client.get(reverse('patient-dashboard'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Welcome back, Alice Wonder!")
        self.assertContains(response, "My Vitals Telemetry")
        self.assertContains(response, "Book an Appointment")

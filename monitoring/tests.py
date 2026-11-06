from django.urls import reverse
from django.contrib.auth import get_user_model
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APITestCase

from accounts.models import User
from patients.models import PatientProfile
from devices.models import Device
from monitoring.models import VitalReading, AlertRule, Alert
from monitoring.services import evaluate_reading

User = get_user_model()


class VitalIngestionAPITests(APITestCase):
    def setUp(self):
        # Create users
        self.patient = User.objects.create_user(
            username='test.patient',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='Test',
            last_name='Patient',
        )
        self.profile = PatientProfile.objects.create(
            user=self.patient,
            age=50,
            gender='male',
            blood_group='O+',
        )

        # Create Device
        self.device = Device.objects.create(
            device_id='TEST-POX-001',
            device_type=Device.DeviceType.PULSE_OXIMETER,
            patient=self.patient,
            api_key='test_valid_api_key_12345',
            is_active=True,
        )

        # Create Alert Rule
        self.spo2_rule = AlertRule.objects.create(
            vital_type='spo2',
            min_value=92.0,
            max_value=None,
            severity='critical',
            description='Low oxygen saturation',
            is_active=True,
        )

        self.url = reverse('vital-ingest')

    def test_ingest_telemetry_success(self):
        """Test that a valid API key and payload correctly ingests telemetry and updates device.last_seen."""
        payload = {
            'vital_type': 'spo2',
            'value': 98.0,
            'unit': '%',
        }
        response = self.client.post(
            self.url,
            data=payload,
            format='json',
            HTTP_X_API_KEY=self.device.api_key
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['status'], 'success')
        self.assertEqual(response.data['alerts_triggered'], 0)

        # Verify database record
        reading = VitalReading.objects.filter(device=self.device).first()
        self.assertIsNotNone(reading)
        self.assertEqual(reading.vital_type, 'spo2')
        self.assertEqual(reading.value, 98.0)
        self.assertEqual(reading.patient, self.patient)

        # Verify device last_seen was updated
        self.device.refresh_from_db()
        self.assertIsNotNone(self.device.last_seen)

    def test_missing_api_key_returns_401(self):
        """Test that requests without X-API-KEY header are rejected."""
        payload = {
            'vital_type': 'spo2',
            'value': 97.0,
            'unit': '%',
        }
        response = self.client.post(self.url, data=payload, format='json')
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Missing 'X-API-KEY'", response.data['error'])

    def test_invalid_api_key_returns_401(self):
        """Test that requests with an unrecognized API key are rejected."""
        payload = {
            'vital_type': 'spo2',
            'value': 97.0,
            'unit': '%',
        }
        response = self.client.post(
            self.url,
            data=payload,
            format='json',
            HTTP_X_API_KEY='non_existent_api_key_xyz'
        )
        self.assertEqual(response.status_code, status.HTTP_401_UNAUTHORIZED)
        self.assertIn("Invalid API key", response.data['error'])

    def test_deactivated_device_returns_403(self):
        """Test that telemetry from deactivated devices is rejected with 403."""
        self.device.is_active = False
        self.device.save()

        payload = {
            'vital_type': 'spo2',
            'value': 97.0,
            'unit': '%',
        }
        response = self.client.post(
            self.url,
            data=payload,
            format='json',
            HTTP_X_API_KEY=self.device.api_key
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)
        self.assertIn("Device is deactivated", response.data['error'])

    def test_ingestion_triggers_alert_when_threshold_violated(self):
        """Test that abnormal reading triggers an alert during ingestion."""
        payload = {
            'vital_type': 'spo2',
            'value': 89.0,  # Below min 92.0 -> triggers alert
            'unit': '%',
        }
        response = self.client.post(
            self.url,
            data=payload,
            format='json',
            HTTP_X_API_KEY=self.device.api_key
        )

        self.assertEqual(response.status_code, status.HTTP_201_CREATED)
        self.assertEqual(response.data['alerts_triggered'], 1)
        self.assertEqual(len(response.data['alerts']), 1)
        self.assertEqual(response.data['alerts'][0]['status'], 'open')

        # Check Alert in DB
        alert = Alert.objects.filter(reading__value=89.0).first()
        self.assertIsNotNone(alert)
        self.assertEqual(alert.status, 'open')
        self.assertEqual(alert.rule, self.spo2_rule)


class AlertEngineServiceTests(APITestCase):
    def setUp(self):
        self.patient = User.objects.create_user(
            username='alert.test.patient',
            password='Password123!',
            role=User.Role.PATIENT,
        )
        self.hr_rule = AlertRule.objects.create(
            vital_type='heart_rate',
            min_value=50.0,
            max_value=100.0,
            severity='high',
            is_active=True,
        )
        self.glucose_rule = AlertRule.objects.create(
            vital_type='blood_glucose',
            min_value=70.0,
            max_value=180.0,
            severity='critical',
            is_active=True,
        )

    def test_normal_reading_no_alert(self):
        """Normal reading within boundaries should not generate alerts."""
        reading = VitalReading.objects.create(
            patient=self.patient,
            vital_type='heart_rate',
            value=75.0,
            unit='bpm',
        )
        alerts = evaluate_reading(reading)
        self.assertEqual(len(alerts), 0)
        self.assertEqual(Alert.objects.filter(reading=reading).count(), 0)

    def test_value_exceeding_max_triggers_alert(self):
        """Reading with value exceeding max_value triggers alert."""
        reading = VitalReading.objects.create(
            patient=self.patient,
            vital_type='heart_rate',
            value=122.0,  # > 100.0
            unit='bpm',
        )
        alerts = evaluate_reading(reading)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule, self.hr_rule)
        self.assertEqual(alerts[0].status, 'open')

    def test_value_below_min_triggers_alert(self):
        """Reading with value below min_value triggers alert."""
        reading = VitalReading.objects.create(
            patient=self.patient,
            vital_type='blood_glucose',
            value=54.0,  # < 70.0
            unit='mg/dL',
        )
        alerts = evaluate_reading(reading)
        self.assertEqual(len(alerts), 1)
        self.assertEqual(alerts[0].rule, self.glucose_rule)

    def test_inactive_rule_not_evaluated(self):
        """Inactive rules should not trigger alerts."""
        self.hr_rule.is_active = False
        self.hr_rule.save()

        reading = VitalReading.objects.create(
            patient=self.patient,
            vital_type='heart_rate',
            value=150.0,
            unit='bpm',
        )
        alerts = evaluate_reading(reading)
        self.assertEqual(len(alerts), 0)


class AlertResolutionAndVitalsQueryTests(APITestCase):
    def setUp(self):
        self.doctor = User.objects.create_user(
            username='doctor.smith',
            password='DoctorPassword123!',
            role=User.Role.DOCTOR,
            first_name='John',
            last_name='Smith',
        )
        self.patient = User.objects.create_user(
            username='patient.alice',
            password='PatientPassword123!',
            role=User.Role.PATIENT,
            first_name='Alice',
            last_name='Brown',
        )
        self.other_patient = User.objects.create_user(
            username='patient.bob',
            password='PatientPassword123!',
            role=User.Role.PATIENT,
        )

        self.reading = VitalReading.objects.create(
            patient=self.patient,
            vital_type='systolic_bp',
            value=155.0,
            unit='mmHg',
        )
        self.alert = Alert.objects.create(
            reading=self.reading,
            status='open',
        )

    def test_doctor_can_resolve_alert(self):
        """Doctors can resolve an open alert."""
        self.client.force_authenticate(user=self.doctor)
        url = reverse('alert-resolve', kwargs={'alert_id': self.alert.id})
        response = self.client.patch(
            url,
            data={'resolution_notes': 'Prescribed ACE inhibitor adjustment.'},
            format='json'
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.alert.refresh_from_db()
        self.assertEqual(self.alert.status, 'resolved')
        self.assertEqual(self.alert.resolved_by, self.doctor)
        self.assertIn('ACE inhibitor', self.alert.resolution_notes)

    def test_patient_cannot_resolve_alert(self):
        """Patients are not permitted to resolve alerts."""
        self.client.force_authenticate(user=self.patient)
        url = reverse('alert-resolve', kwargs={'alert_id': self.alert.id})
        response = self.client.patch(
            url,
            data={'resolution_notes': 'Trying to resolve myself'},
            format='json'
        )
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_patient_can_view_own_vitals(self):
        """Patient can view their own vitals list."""
        self.client.force_authenticate(user=self.patient)
        url = reverse('patient-vitals', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

    def test_patient_cannot_view_another_patient_vitals(self):
        """Patient cannot view another patient's vitals (permission check)."""
        self.client.force_authenticate(user=self.patient)
        url = reverse('patient-vitals', kwargs={'patient_id': self.other_patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_403_FORBIDDEN)

    def test_doctor_can_view_any_patient_vitals(self):
        """Doctor can view any patient's vitals."""
        self.client.force_authenticate(user=self.doctor)
        url = reverse('patient-vitals', kwargs={'patient_id': self.patient.id})
        response = self.client.get(url)
        self.assertEqual(response.status_code, status.HTTP_200_OK)

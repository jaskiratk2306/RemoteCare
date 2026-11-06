from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User
from devices.models import Device


class DevicesAdminFrontendTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin = User.objects.create_user(
            username='admin_dev',
            password='Password123!',
            role=User.Role.ADMIN
        )
        self.patient = User.objects.create_user(
            username='patient_dev',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='Bob',
            last_name='Ross'
        )
        self.other_patient = User.objects.create_user(
            username='patient_dev2',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='Charlie',
            last_name='Brown'
        )
        self.device = Device.objects.create(
            device_id='DEV-BPM-99',
            device_type=Device.DeviceType.BP_MONITOR,
            patient=self.patient,
            model_name='Omron 7000'
        )

    def test_admin_devices_page_renders(self):
        """Admin can access device management portal with stats and inventory"""
        self.client.login(username='admin_dev', password='Password123!')
        response = self.client.get(reverse('admin-devices'))

        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Biomedical Device Management")
        self.assertContains(response, "DEV-BPM-99")
        self.assertContains(response, "Register Biomedical Device")

    def test_device_registration(self):
        """Admin can register a new device and receive auto-generated API key"""
        self.client.login(username='admin_dev', password='Password123!')
        response = self.client.post(reverse('device-create'), {
            'device_id': 'DEV-GLU-555',
            'device_type': Device.DeviceType.GLUCOMETER,
            'model_name': 'Accu-Chek Smart',
            'firmware_version': 'v1.0.0',
            'patient': self.patient.id,
            'is_active': True,
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.assertTrue(Device.objects.filter(device_id='DEV-GLU-555').exists())
        new_dev = Device.objects.get(device_id='DEV-GLU-555')
        self.assertTrue(new_dev.api_key.startswith('rc_dev_'))
        self.assertEqual(new_dev.patient, self.patient)
        self.assertContains(response, "DEV-GLU-555")

    def test_device_reassignment(self):
        """Admin can reassign device to a different patient"""
        self.client.login(username='admin_dev', password='Password123!')
        response = self.client.post(reverse('device-reassign', kwargs={'device_id': self.device.id}), {
            'patient_id': self.other_patient.id
        }, follow=True)

        self.assertEqual(response.status_code, 200)
        self.device.refresh_from_db()
        self.assertEqual(self.device.patient, self.other_patient)

    def test_device_toggle_active(self):
        """Admin can toggle device active/inactive status"""
        self.client.login(username='admin_dev', password='Password123!')
        self.assertTrue(self.device.is_active)

        response = self.client.post(reverse('device-toggle-active', kwargs={'device_id': self.device.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.device.refresh_from_db()
        self.assertFalse(self.device.is_active)

    def test_device_regenerate_api_key(self):
        """Admin can regenerate device API key"""
        self.client.login(username='admin_dev', password='Password123!')
        old_key = self.device.api_key

        response = self.client.post(reverse('device-regenerate-key', kwargs={'device_id': self.device.id}), follow=True)
        self.assertEqual(response.status_code, 200)
        self.device.refresh_from_db()
        self.assertNotEqual(self.device.api_key, old_key)
        self.assertTrue(self.device.api_key.startswith('rc_dev_'))

from django.test import TestCase, Client
from django.urls import reverse
from accounts.models import User


class AccountsFrontendTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.admin_user = User.objects.create_user(
            username='admin_test',
            password='Password123!',
            role=User.Role.ADMIN,
            first_name='Admin',
            last_name='User'
        )
        self.doctor_user = User.objects.create_user(
            username='doctor_test',
            password='Password123!',
            role=User.Role.DOCTOR,
            first_name='Doctor',
            last_name='Who'
        )
        self.patient_user = User.objects.create_user(
            username='patient_test',
            password='Password123!',
            role=User.Role.PATIENT,
            first_name='John',
            last_name='Doe'
        )

    def test_unauthenticated_root_redirects_to_login(self):
        """Visiting root when unauthenticated redirects to /login/"""
        response = self.client.get(reverse('home-redirect'))
        self.assertRedirects(response, reverse('login'))

    def test_login_page_renders_with_demo_accounts(self):
        """Login page displays RemoteCare branding and demo accounts"""
        response = self.client.get(reverse('login'))
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "RemoteCare Portal")
        self.assertContains(response, "dr.chen")
        self.assertContains(response, "patient.johndoe")

    def test_doctor_login_redirects_to_doctor_dashboard(self):
        """Logging in as Doctor redirects to doctor dashboard"""
        response = self.client.post(reverse('login'), {
            'username': 'doctor_test',
            'password': 'Password123!'
        })
        self.assertRedirects(response, reverse('doctor-dashboard'))

    def test_patient_login_redirects_to_patient_dashboard(self):
        """Logging in as Patient redirects to patient dashboard"""
        response = self.client.post(reverse('login'), {
            'username': 'patient_test',
            'password': 'Password123!'
        })
        self.assertRedirects(response, reverse('patient-dashboard'))

    def test_admin_login_redirects_to_admin_devices(self):
        """Logging in as Admin redirects to admin devices management"""
        response = self.client.post(reverse('login'), {
            'username': 'admin_test',
            'password': 'Password123!'
        })
        self.assertRedirects(response, reverse('admin-devices'))

    def test_invalid_login_shows_error(self):
        """Invalid credentials show error feedback"""
        response = self.client.post(reverse('login'), {
            'username': 'doctor_test',
            'password': 'WrongPassword'
        })
        self.assertEqual(response.status_code, 200)
        self.assertContains(response, "Invalid username or password")

    def test_logout(self):
        """Logout redirects to login"""
        self.client.login(username='doctor_test', password='Password123!')
        response = self.client.post(reverse('logout'))
        self.assertRedirects(response, reverse('login'))

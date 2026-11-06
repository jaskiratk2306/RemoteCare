from django.contrib.auth.models import AbstractUser
from django.db import models


class User(AbstractUser):
    class Role(models.TextChoices):
        ADMIN = 'admin', 'Admin'
        DOCTOR = 'doctor', 'Doctor'
        PATIENT = 'patient', 'Patient'

    role = models.CharField(
        max_length=20,
        choices=Role.choices,
        default=Role.PATIENT,
        help_text="Designates the user role in RemoteCare (Admin, Doctor, Patient)."
    )
    phone_number = models.CharField(max_length=25, blank=True, null=True)

    class Meta:
        verbose_name = 'User'
        verbose_name_plural = 'Users'
        ordering = ['username']

    def __str__(self):
        full_name = self.get_full_name()
        display = full_name if full_name else self.username
        return f"{display} ({self.get_role_display()})"

    @property
    def is_doctor(self):
        return self.role == self.Role.DOCTOR

    @property
    def is_patient(self):
        return self.role == self.Role.PATIENT

    @property
    def is_admin_role(self):
        return self.role == self.Role.ADMIN or self.is_superuser or self.is_staff

from django.db import models
from django.conf import settings


class PatientProfile(models.Model):
    GENDER_CHOICES = [
        ('male', 'Male'),
        ('female', 'Female'),
        ('other', 'Other'),
    ]

    BLOOD_GROUP_CHOICES = [
        ('A+', 'A+'),
        ('A-', 'A-'),
        ('B+', 'B+'),
        ('B-', 'B-'),
        ('AB+', 'AB+'),
        ('AB-', 'AB-'),
        ('O+', 'O+'),
        ('O-', 'O-'),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='patient_profile',
        limit_choices_to={'role': 'patient'}
    )
    age = models.PositiveIntegerField(null=True, blank=True)
    gender = models.CharField(max_length=10, choices=GENDER_CHOICES, blank=True)
    blood_group = models.CharField(max_length=5, choices=BLOOD_GROUP_CHOICES, blank=True)
    medical_history = models.TextField(
        blank=True,
        help_text="Chronic conditions, diagnoses, medications, and allergies."
    )
    assigned_doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='assigned_patients',
        limit_choices_to={'role': 'doctor'}
    )
    emergency_contact = models.CharField(max_length=100, blank=True, help_text="Emergency contact name & phone")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Patient Profile'
        verbose_name_plural = 'Patient Profiles'
        ordering = ['user__last_name', 'user__first_name']

    def __str__(self):
        doctor_name = self.assigned_doctor.get_full_name() if self.assigned_doctor else "Unassigned"
        return f"{self.user.get_full_name() or self.user.username} (Doctor: {doctor_name})"


class ClinicalNote(models.Model):
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clinical_notes_received',
        limit_choices_to={'role': 'patient'}
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='clinical_notes_written',
        limit_choices_to={'role': 'doctor'}
    )
    note = models.TextField(help_text="Clinical observations, care plans, and instructions.")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Clinical Note'
        verbose_name_plural = 'Clinical Notes'
        ordering = ['-created_at']

    def __str__(self):
        return f"Note for {self.patient.username} by {self.doctor.username} on {self.created_at.strftime('%Y-%m-%d %H:%M')}"

from django.db import models
from django.conf import settings


class Appointment(models.Model):
    class Status(models.TextChoices):
        SCHEDULED = 'scheduled', 'Scheduled'
        COMPLETED = 'completed', 'Completed'
        CANCELLED = 'cancelled', 'Cancelled'

    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments_as_patient',
        limit_choices_to={'role': 'patient'},
        help_text="The patient attending this appointment."
    )
    doctor = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='appointments_as_doctor',
        limit_choices_to={'role': 'doctor'},
        help_text="The attending doctor."
    )
    datetime = models.DateTimeField(
        help_text="Scheduled date and time of the clinical consultation."
    )
    status = models.CharField(
        max_length=20,
        choices=Status.choices,
        default=Status.SCHEDULED,
        db_index=True
    )
    reason = models.TextField(
        help_text="Clinical justification, reason for consultation, or follow-up notes."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Appointment'
        verbose_name_plural = 'Appointments'
        ordering = ['datetime']

    def __str__(self):
        pat = self.patient.get_full_name() or self.patient.username
        doc = self.doctor.get_full_name() or self.doctor.username
        return f"{self.datetime.strftime('%Y-%m-%d %H:%M')} | {pat} with Dr. {doc} [{self.get_status_display()}]"

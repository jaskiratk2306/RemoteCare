import secrets
from django.db import models
from django.conf import settings


def generate_device_api_key():
    """Generates a secure, cryptographically random API key for device authentication."""
    return f"rc_dev_{secrets.token_urlsafe(28)}"


class Device(models.Model):
    class DeviceType(models.TextChoices):
        PULSE_OXIMETER = 'pulse_oximeter', 'Pulse Oximeter'
        BP_MONITOR = 'bp_monitor', 'Blood Pressure Monitor'
        GLUCOMETER = 'glucometer', 'Glucometer'
        THERMOMETER = 'thermometer', 'Thermometer'

    device_id = models.CharField(
        max_length=64,
        unique=True,
        help_text="Unique hardware serial number or identifier (e.g. POX-1001, BPM-2002)."
    )
    device_type = models.CharField(
        max_length=32,
        choices=DeviceType.choices,
        help_text="Biomedical device category."
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='devices',
        limit_choices_to={'role': 'patient'},
        help_text="Patient to whom this device is currently assigned."
    )
    api_key = models.CharField(
        max_length=64,
        unique=True,
        db_index=True,
        default=generate_device_api_key,
        help_text="Auto-generated API key used in X-API-KEY header for IoT ingestion."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether the device is permitted to ingest telemetry data."
    )
    last_seen = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the most recent valid telemetry received from this device."
    )
    model_name = models.CharField(max_length=100, blank=True, help_text="Hardware make/model")
    firmware_version = models.CharField(max_length=32, blank=True, default="v1.0.0")
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Biomedical Device'
        verbose_name_plural = 'Biomedical Devices'
        ordering = ['-created_at']

    def __str__(self):
        return f"{self.device_id} ({self.get_device_type_display()}) -> {self.patient.username}"

    def regenerate_api_key(self):
        """Regenerate a fresh API key and save."""
        self.api_key = generate_device_api_key()
        self.save(update_fields=['api_key', 'updated_at'])
        return self.api_key

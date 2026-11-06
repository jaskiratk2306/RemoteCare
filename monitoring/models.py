from django.db import models
from django.conf import settings
from django.utils import timezone


class VitalReading(models.Model):
    VITAL_TYPE_CHOICES = [
        ('heart_rate', 'Heart Rate'),
        ('spo2', 'Oxygen Saturation (SpO2)'),
        ('systolic_bp', 'Systolic Blood Pressure'),
        ('diastolic_bp', 'Diastolic Blood Pressure'),
        ('blood_glucose', 'Blood Glucose'),
        ('temperature', 'Body Temperature'),
    ]

    device = models.ForeignKey(
        'devices.Device',
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='readings',
        help_text="The biomedical device that collected this reading."
    )
    patient = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name='vital_readings',
        limit_choices_to={'role': 'patient'},
        help_text="The patient associated with this vital reading."
    )
    vital_type = models.CharField(
        max_length=50,
        choices=VITAL_TYPE_CHOICES,
        help_text="Type of biometric data recorded."
    )
    value = models.FloatField(help_text="Recorded numerical measurement.")
    unit = models.CharField(max_length=20, help_text="Measurement unit (e.g., bpm, %, mmHg, mg/dL, °C).")
    timestamp = models.DateTimeField(
        default=timezone.now,
        db_index=True,
        help_text="Timestamp when the reading was taken."
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = 'Vital Reading'
        verbose_name_plural = 'Vital Readings'
        ordering = ['-timestamp']
        indexes = [
            models.Index(fields=['patient', 'vital_type', '-timestamp']),
        ]

    def __str__(self):
        return f"{self.patient.username} - {self.get_vital_type_display()}: {self.value} {self.unit} @ {self.timestamp.strftime('%Y-%m-%d %H:%M:%S')}"


class AlertRule(models.Model):
    SEVERITY_CHOICES = [
        ('low', 'Low'),
        ('medium', 'Medium'),
        ('high', 'High'),
        ('critical', 'Critical'),
    ]

    vital_type = models.CharField(
        max_length=50,
        choices=VitalReading.VITAL_TYPE_CHOICES,
        help_text="The vital parameter this rule governs."
    )
    min_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Readings below this threshold trigger an alert."
    )
    max_value = models.FloatField(
        null=True,
        blank=True,
        help_text="Readings above this threshold trigger an alert."
    )
    severity = models.CharField(
        max_length=20,
        choices=SEVERITY_CHOICES,
        default='medium',
        help_text="Severity level assigned to triggered alerts."
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this rule is actively evaluated during telemetry ingestion."
    )
    description = models.CharField(
        max_length=255,
        blank=True,
        help_text="Clinical guidance or description for this rule."
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = 'Alert Rule'
        verbose_name_plural = 'Alert Rules'
        ordering = ['vital_type', 'severity']

    def __str__(self):
        conds = []
        if self.min_value is not None:
            conds.append(f"< {self.min_value}")
        if self.max_value is not None:
            conds.append(f"> {self.max_value}")
        threshold_str = " or ".join(conds) if conds else "No threshold"
        return f"{self.get_vital_type_display()} [{self.get_severity_display()}] ({threshold_str})"

    def is_triggered(self, val: float) -> bool:
        """Evaluates whether the provided numerical value violates this threshold rule."""
        if not self.is_active:
            return False
        if self.min_value is not None and val < self.min_value:
            return True
        if self.max_value is not None and val > self.max_value:
            return True
        return False


class Alert(models.Model):
    STATUS_CHOICES = [
        ('open', 'Open'),
        ('resolved', 'Resolved'),
    ]

    reading = models.ForeignKey(
        VitalReading,
        on_delete=models.CASCADE,
        related_name='alerts',
        help_text="The vital reading that triggered this alert."
    )
    rule = models.ForeignKey(
        AlertRule,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='alerts',
        help_text="The threshold rule that was violated."
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default='open',
        db_index=True,
        help_text="Current clinical triage status."
    )
    resolved_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name='resolved_alerts',
        limit_choices_to={'role__in': ['doctor', 'admin']},
        help_text="Medical staff member who triaged and resolved the alert."
    )
    resolved_at = models.DateTimeField(null=True, blank=True)
    resolution_notes = models.TextField(blank=True, help_text="Doctor notes documenting the resolution.")
    created_at = models.DateTimeField(auto_now_add=True, db_index=True)

    class Meta:
        verbose_name = 'Biomedical Alert'
        verbose_name_plural = 'Biomedical Alerts'
        ordering = ['-created_at']

    def __str__(self):
        patient_name = self.reading.patient.get_full_name() or self.reading.patient.username
        severity = self.rule.get_severity_display() if self.rule else "Warning"
        return f"[{severity.upper()}] {self.reading.vital_type}={self.reading.value} ({patient_name}) - {self.status.upper()}"

    def mark_resolved(self, user, notes=""):
        """Marks this alert as resolved by a specific doctor/admin."""
        self.status = 'resolved'
        self.resolved_by = user
        self.resolved_at = timezone.now()
        if notes:
            self.resolution_notes = notes
        self.save(update_fields=['status', 'resolved_by', 'resolved_at', 'resolution_notes'])

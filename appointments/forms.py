from django import forms
from django.utils import timezone
from .models import Appointment
from accounts.models import User


class AppointmentBookingForm(forms.ModelForm):
    doctor = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.DOCTOR, is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Attending Doctor",
        empty_label="-- Select Doctor --"
    )
    datetime = forms.DateTimeField(
        widget=forms.DateTimeInput(attrs={
            'type': 'datetime-local',
            'class': 'form-control',
            'placeholder': 'YYYY-MM-DD HH:MM'
        }),
        label="Appointment Date & Time"
    )
    reason = forms.CharField(
        widget=forms.Textarea(attrs={
            'class': 'form-control',
            'rows': 3,
            'placeholder': 'State the clinical reason for consultation, key symptoms, or monitoring follow-up...'
        }),
        label="Reason for Consultation"
    )

    class Meta:
        model = Appointment
        fields = ['doctor', 'datetime', 'reason']

    def clean_datetime(self):
        dt = self.cleaned_data.get('datetime')
        if dt and dt < timezone.now():
            raise forms.ValidationError("Appointment time cannot be in the past. Please select an upcoming slot.")
        return dt


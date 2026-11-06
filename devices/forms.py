from django import forms
from .models import Device
from accounts.models import User


class DeviceRegistrationForm(forms.ModelForm):
    patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.PATIENT, is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="Assign to Patient",
        empty_label="-- Select Patient --"
    )

    class Meta:
        model = Device
        fields = [
            'device_id',
            'device_type',
            'model_name',
            'firmware_version',
            'patient',
            'is_active',
        ]
        widgets = {
            'device_id': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., POX-1090, BPM-2050, GLU-3010, THM-4015',
                'autocomplete': 'off',
            }),
            'device_type': forms.Select(attrs={'class': 'form-select'}),
            'model_name': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., Nonin 3150 WristOx, Omron Complete',
            }),
            'firmware_version': forms.TextInput(attrs={
                'class': 'form-control',
                'placeholder': 'e.g., v1.0.0',
            }),
            'is_active': forms.CheckboxInput(attrs={'class': 'form-check-input'}),
        }
        labels = {
            'device_id': 'Hardware Serial / Device Identifier',
            'device_type': 'Biomedical Category',
            'model_name': 'Make / Hardware Model',
            'firmware_version': 'Firmware Version',
            'is_active': 'Active for Telemetry Ingestion',
        }


class DeviceReassignForm(forms.Form):
    patient = forms.ModelChoiceField(
        queryset=User.objects.filter(role=User.Role.PATIENT, is_active=True),
        widget=forms.Select(attrs={'class': 'form-select'}),
        label="New Assigned Patient"
    )


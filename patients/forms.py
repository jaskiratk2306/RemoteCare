from django import forms
from .models import ClinicalNote


class ClinicalNoteForm(forms.ModelForm):
    class Meta:
        model = ClinicalNote
        fields = ['note']
        widgets = {
            'note': forms.Textarea(attrs={
                'class': 'form-control',
                'rows': 4,
                'placeholder': 'Document patient status, medication adjustments, diagnostic thoughts, or care instructions...',
                'required': True,
            }),
        }
        labels = {
            'note': 'Clinical Note Content',
        }


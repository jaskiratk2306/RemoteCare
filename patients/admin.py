from django.contrib import admin
from .models import PatientProfile, ClinicalNote


class ClinicalNoteInline(admin.TabularInline):
    model = ClinicalNote
    extra = 0
    fk_name = 'patient'
    fields = ['doctor', 'note', 'created_at']
    readonly_fields = ['created_at']


@admin.register(PatientProfile)
class PatientProfileAdmin(admin.ModelAdmin):
    list_display = [
        'get_patient_name',
        'get_username',
        'age',
        'gender',
        'blood_group',
        'assigned_doctor',
        'emergency_contact',
        'created_at',
    ]
    list_filter = ['gender', 'blood_group', 'assigned_doctor']
    search_fields = [
        'user__username',
        'user__first_name',
        'user__last_name',
        'user__email',
        'medical_history',
        'assigned_doctor__first_name',
        'assigned_doctor__last_name',
    ]
    autocomplete_fields = []
    readonly_fields = ['created_at', 'updated_at']

    @admin.display(description='Patient Name')
    def get_patient_name(self, obj):
        return obj.user.get_full_name() or obj.user.username

    @admin.display(description='Username')
    def get_username(self, obj):
        return obj.user.username


@admin.register(ClinicalNote)
class ClinicalNoteAdmin(admin.ModelAdmin):
    list_display = ['id', 'patient', 'doctor', 'short_note', 'created_at']
    list_filter = ['doctor', 'created_at']
    search_fields = [
        'patient__username',
        'patient__first_name',
        'patient__last_name',
        'doctor__username',
        'doctor__first_name',
        'doctor__last_name',
        'note',
    ]
    readonly_fields = ['created_at']

    @admin.display(description='Note Preview')
    def short_note(self, obj):
        return obj.note[:80] + '...' if len(obj.note) > 80 else obj.note

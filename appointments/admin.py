from django.contrib import admin
from .models import Appointment


@admin.register(Appointment)
class AppointmentAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'datetime',
        'get_patient_name',
        'get_doctor_name',
        'status',
        'short_reason',
        'created_at',
    ]
    list_filter = ['status', 'datetime', 'doctor']
    search_fields = [
        'patient__username',
        'patient__first_name',
        'patient__last_name',
        'doctor__username',
        'doctor__first_name',
        'doctor__last_name',
        'reason',
    ]
    date_hierarchy = 'datetime'
    actions = ['mark_completed', 'mark_cancelled']

    @admin.display(description='Patient')
    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    @admin.display(description='Doctor')
    def get_doctor_name(self, obj):
        return f"Dr. {obj.doctor.get_full_name() or obj.doctor.username}"

    @admin.display(description='Reason')
    def short_reason(self, obj):
        return obj.reason[:60] + '...' if len(obj.reason) > 60 else obj.reason

    @admin.action(description="Mark selected appointments as Completed")
    def mark_completed(self, request, queryset):
        count = queryset.update(status=Appointment.Status.COMPLETED)
        self.message_user(request, f"{count} appointment(s) marked as completed.")

    @admin.action(description="Mark selected appointments as Cancelled")
    def mark_cancelled(self, request, queryset):
        count = queryset.update(status=Appointment.Status.CANCELLED)
        self.message_user(request, f"{count} appointment(s) marked as cancelled.")

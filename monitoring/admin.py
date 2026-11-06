from django.contrib import admin
from django.utils import timezone
from .models import VitalReading, AlertRule, Alert


@admin.register(VitalReading)
class VitalReadingAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'get_patient_name',
        'vital_type',
        'value_with_unit',
        'get_device_id',
        'timestamp',
        'created_at',
    ]
    list_filter = ['vital_type', 'timestamp', 'device__device_type']
    search_fields = [
        'patient__username',
        'patient__first_name',
        'patient__last_name',
        'device__device_id',
    ]
    readonly_fields = ['created_at']
    date_hierarchy = 'timestamp'

    @admin.display(description='Patient')
    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    @admin.display(description='Value')
    def value_with_unit(self, obj):
        return f"{obj.value} {obj.unit}"

    @admin.display(description='Device')
    def get_device_id(self, obj):
        return obj.device.device_id if obj.device else "Manual/Direct"


@admin.register(AlertRule)
class AlertRuleAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'vital_type',
        'min_value',
        'max_value',
        'severity_badge',
        'is_active',
        'description',
        'updated_at',
    ]
    list_filter = ['vital_type', 'severity', 'is_active']
    search_fields = ['vital_type', 'description']
    actions = ['activate_rules', 'deactivate_rules']

    @admin.display(description='Severity')
    def severity_badge(self, obj):
        return obj.get_severity_display().upper()

    @admin.action(description="Activate selected alert rules")
    def activate_rules(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} rule(s) activated.")

    @admin.action(description="Deactivate selected alert rules")
    def deactivate_rules(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} rule(s) deactivated.")


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = [
        'id',
        'status_tag',
        'get_patient',
        'vital_summary',
        'rule_severity',
        'resolved_by',
        'created_at',
    ]
    list_filter = ['status', 'rule__severity', 'rule__vital_type', 'created_at']
    search_fields = [
        'reading__patient__username',
        'reading__patient__first_name',
        'reading__patient__last_name',
        'resolved_by__username',
        'resolution_notes',
    ]
    readonly_fields = ['created_at', 'resolved_at']
    actions = ['resolve_alerts']

    @admin.display(description='Status')
    def status_tag(self, obj):
        return obj.status.upper()

    @admin.display(description='Patient')
    def get_patient(self, obj):
        return obj.reading.patient.get_full_name() or obj.reading.patient.username

    @admin.display(description='Reading')
    def vital_summary(self, obj):
        return f"{obj.reading.vital_type}: {obj.reading.value} {obj.reading.unit}"

    @admin.display(description='Severity')
    def rule_severity(self, obj):
        return obj.rule.get_severity_display().upper() if obj.rule else "UNKNOWN"

    @admin.action(description="Resolve selected alerts")
    def resolve_alerts(self, request, queryset):
        updated = 0
        for alert in queryset.filter(status='open'):
            alert.mark_resolved(user=request.user, notes="Resolved via bulk admin action.")
            updated += 1
        self.message_user(request, f"{updated} open alert(s) marked as resolved.")

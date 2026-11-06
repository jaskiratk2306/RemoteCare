from django.contrib import admin
from .models import Device


@admin.register(Device)
class DeviceAdmin(admin.ModelAdmin):
    list_display = [
        'device_id',
        'device_type',
        'get_patient_name',
        'is_active',
        'last_seen',
        'masked_api_key',
        'firmware_version',
        'created_at',
    ]
    list_filter = ['device_type', 'is_active', 'created_at']
    search_fields = [
        'device_id',
        'patient__username',
        'patient__first_name',
        'patient__last_name',
        'patient__email',
        'model_name',
    ]
    readonly_fields = ['api_key', 'last_seen', 'created_at', 'updated_at']
    actions = ['activate_devices', 'deactivate_devices', 'rotate_api_keys']

    @admin.display(description='Patient')
    def get_patient_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username

    @admin.display(description='API Key')
    def masked_api_key(self, obj):
        if not obj.api_key:
            return "-"
        return f"{obj.api_key[:10]}...{obj.api_key[-6:]}"

    @admin.action(description="Mark selected devices as Active")
    def activate_devices(self, request, queryset):
        count = queryset.update(is_active=True)
        self.message_user(request, f"{count} device(s) activated successfully.")

    @admin.action(description="Mark selected devices as Inactive")
    def deactivate_devices(self, request, queryset):
        count = queryset.update(is_active=False)
        self.message_user(request, f"{count} device(s) deactivated successfully.")

    @admin.action(description="Regenerate API keys for selected devices")
    def rotate_api_keys(self, request, queryset):
        for device in queryset:
            device.regenerate_api_key()
        self.message_user(request, f"API keys rotated for {queryset.count()} device(s).")

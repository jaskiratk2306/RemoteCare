from django.urls import path
from .views import (
    admin_devices_view,
    device_create_view,
    device_reassign_view,
    device_toggle_active_view,
    device_regenerate_key_view,
)

urlpatterns = [
    path('admin-portal/devices/', admin_devices_view, name='admin-devices'),
    path('admin-portal/devices/create/', device_create_view, name='device-create'),
    path('admin-portal/devices/<int:device_id>/reassign/', device_reassign_view, name='device-reassign'),
    path('admin-portal/devices/<int:device_id>/toggle-active/', device_toggle_active_view, name='device-toggle-active'),
    path('admin-portal/devices/<int:device_id>/regenerate-key/', device_regenerate_key_view, name='device-regenerate-key'),
]


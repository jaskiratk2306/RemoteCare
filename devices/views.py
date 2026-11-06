from datetime import timedelta
from django.shortcuts import render, redirect, get_object_or_404
from django.contrib import messages
from django.utils import timezone
from django.db.models import Q
from accounts.decorators import admin_required
from accounts.models import User
from .models import Device
from .forms import DeviceRegistrationForm


@admin_required
def admin_devices_view(request):
    """
    Admin portal for biomedical device inventory, registration, and patient assignment.
    """
    # Filtering parameters
    search_query = request.GET.get('q', '').strip()
    device_type = request.GET.get('type', '').strip()
    status_filter = request.GET.get('status', '').strip()

    queryset = Device.objects.select_related('patient', 'patient__patient_profile').order_by('-created_at')

    if search_query:
        queryset = queryset.filter(
            Q(device_id__icontains=search_query) |
            Q(model_name__icontains=search_query) |
            Q(patient__username__icontains=search_query) |
            Q(patient__first_name__icontains=search_query) |
            Q(patient__last_name__icontains=search_query)
        )

    if device_type:
        queryset = queryset.filter(device_type=device_type)

    if status_filter == 'active':
        queryset = queryset.filter(is_active=True)
    elif status_filter == 'inactive':
        queryset = queryset.filter(is_active=False)

    # Telemetry statistics
    one_day_ago = timezone.now() - timedelta(hours=24)
    total_devices = Device.objects.count()
    active_devices = Device.objects.filter(is_active=True).count()
    inactive_devices = Device.objects.filter(is_active=False).count()
    online_devices_24h = Device.objects.filter(last_seen__gte=one_day_ago).count()

    # Patients list for assignment modals
    all_patients = User.objects.filter(role=User.Role.PATIENT, is_active=True).order_by('last_name', 'first_name')

    # Pop newly created device details if stored in session
    new_device_info = request.session.pop('newly_created_device', None)

    form = DeviceRegistrationForm()

    context = {
        'devices': queryset,
        'all_patients': all_patients,
        'form': form,
        'total_devices': total_devices,
        'active_devices': active_devices,
        'inactive_devices': inactive_devices,
        'online_devices_24h': online_devices_24h,
        'search_query': search_query,
        'device_type': device_type,
        'status_filter': status_filter,
        'device_types': Device.DeviceType.choices,
        'new_device_info': new_device_info,
    }
    return render(request, 'devices/admin_devices.html', context)


@admin_required
def device_create_view(request):
    """Registers a new biomedical device with auto-generated secure API key."""
    if request.method != 'POST':
        return redirect('admin-devices')

    form = DeviceRegistrationForm(request.POST)
    if form.is_valid():
        device = form.save()
        # Save key details in session so the admin can copy the freshly generated key
        request.session['newly_created_device'] = {
            'device_id': device.device_id,
            'api_key': device.api_key,
            'device_type': device.get_device_type_display(),
            'patient': device.patient.get_full_name() or device.patient.username,
        }
        messages.success(
            request,
            f"Device '{device.device_id}' registered successfully and assigned to {device.patient.get_full_name() or device.patient.username}."
        )
    else:
        for field, errs in form.errors.items():
            for err in errs:
                messages.error(request, f"{field.replace('_', ' ').capitalize()}: {err}")

    return redirect('admin-devices')


@admin_required
def device_reassign_view(request, device_id):
    """Reassigns an existing biomedical device to another patient."""
    device = get_object_or_404(Device, id=device_id)

    if request.method == 'POST':
        patient_id = request.POST.get('patient_id')
        new_patient = get_object_or_404(User, id=patient_id, role=User.Role.PATIENT)

        old_patient_name = device.patient.get_full_name() or device.patient.username
        device.patient = new_patient
        device.save(update_fields=['patient', 'updated_at'])

        messages.success(
            request,
            f"Device '{device.device_id}' reassigned from {old_patient_name} to {new_patient.get_full_name() or new_patient.username}."
        )

    return redirect('admin-devices')


@admin_required
def device_toggle_active_view(request, device_id):
    """Toggles active status for device ingestion access."""
    device = get_object_or_404(Device, id=device_id)

    if request.method == 'POST':
        device.is_active = not device.is_active
        device.save(update_fields=['is_active', 'updated_at'])

        state = "Activated" if device.is_active else "Deactivated"
        messages.info(
            request,
            f"Device '{device.device_id}' is now {state}."
        )

    return redirect('admin-devices')


@admin_required
def device_regenerate_key_view(request, device_id):
    """Generates a new secure API key for the biomedical hardware device."""
    device = get_object_or_404(Device, id=device_id)

    if request.method == 'POST':
        new_key = device.regenerate_api_key()
        request.session['newly_created_device'] = {
            'device_id': device.device_id,
            'api_key': new_key,
            'device_type': device.get_device_type_display(),
            'patient': device.patient.get_full_name() or device.patient.username,
        }
        messages.warning(
            request,
            f"API key for device '{device.device_id}' has been regenerated. Please update the physical device / simulator."
        )

    return redirect('admin-devices')

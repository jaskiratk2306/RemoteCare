from django.shortcuts import render, get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils import timezone
from django.core.exceptions import PermissionDenied

from accounts.decorators import doctor_required, patient_required
from accounts.models import User
from devices.models import Device
from monitoring.models import VitalReading, Alert
from appointments.models import Appointment
from .models import PatientProfile, ClinicalNote
from .forms import ClinicalNoteForm


@doctor_required
def doctor_dashboard_view(request):
    """
    Doctor clinical dashboard:
    - Assigned patients list with telemetry status and active devices
    - Open clinical alerts with severity badges and triage resolve modal/actions
    - Summary metrics and upcoming consultations
    """
    user = request.user
    alerts_scope = request.GET.get('scope', 'assigned')  # 'assigned' or 'all'

    # Assigned Patients
    if user.is_doctor:
        assigned_profiles = PatientProfile.objects.filter(
            assigned_doctor=user
        ).select_related('user', 'assigned_doctor')
    else:
        # Admins see all patients on the clinical overview
        assigned_profiles = PatientProfile.objects.select_related('user', 'assigned_doctor').all()

    # Enhance patient profiles with live metadata
    patients_data = []
    for prof in assigned_profiles:
        pat_user = prof.user
        pat_devices = Device.objects.filter(patient=pat_user)
        pat_alerts_count = Alert.objects.filter(reading__patient=pat_user, status='open').count()
        last_reading = VitalReading.objects.filter(patient=pat_user).order_by('-timestamp').first()

        patients_data.append({
            'profile': prof,
            'user': pat_user,
            'devices': pat_devices,
            'active_devices_count': pat_devices.filter(is_active=True).count(),
            'open_alerts_count': pat_alerts_count,
            'last_reading': last_reading,
        })

    # Open Alerts Query
    open_alerts_query = Alert.objects.filter(status='open').select_related(
        'reading', 'reading__patient', 'reading__device', 'rule'
    ).order_by('-created_at')

    # If Doctor and scope is 'assigned', filter to their patients
    assigned_patient_ids = [p.user.id for p in assigned_profiles]
    if user.is_doctor and alerts_scope == 'assigned':
        open_alerts = open_alerts_query.filter(reading__patient_id__in=assigned_patient_ids)
    else:
        open_alerts = open_alerts_query

    # Statistics
    total_assigned = len(patients_data)
    total_open_alerts = open_alerts_query.filter(reading__patient_id__in=assigned_patient_ids).count() if user.is_doctor else open_alerts_query.count()
    critical_alerts = open_alerts_query.filter(
        reading__patient_id__in=assigned_patient_ids if user.is_doctor else open_alerts_query.values_list('reading__patient_id', flat=True),
        rule__severity='critical'
    ).count()

    # Upcoming Appointments
    upcoming_appointments = Appointment.objects.filter(
        doctor=user if user.is_doctor else open_alerts_query.first(), # admin fallback
        status=Appointment.Status.SCHEDULED,
        datetime__gte=timezone.now()
    ).select_related('patient').order_by('datetime')[:6] if user.is_doctor else Appointment.objects.filter(
        status=Appointment.Status.SCHEDULED,
        datetime__gte=timezone.now()
    ).select_related('patient', 'doctor').order_by('datetime')[:6]

    context = {
        'patients_data': patients_data,
        'open_alerts': open_alerts,
        'total_assigned': total_assigned,
        'total_open_alerts': total_open_alerts,
        'critical_alerts': critical_alerts,
        'upcoming_appointments': upcoming_appointments,
        'alerts_scope': alerts_scope,
        'now': timezone.now(),
    }
    return render(request, 'patients/doctor_dashboard.html', context)


@login_required
def patient_detail_view(request, patient_id):
    """
    Comprehensive patient clinical telemetry view:
    - Demographics & medical history
    - Live line charts for each vital with 5-second polling
    - Clinical consultation notes history & note authoring
    - Clinical appointments list & scheduling
    """
    patient = get_object_or_404(User, id=patient_id, role=User.Role.PATIENT)

    # Permission check: Patient can only view their own; Doctor/Admin can view any
    if request.user.is_patient and request.user.id != patient.id:
        raise PermissionDenied("You do not have permission to view telemetry for this patient.")

    profile = getattr(patient, 'patient_profile', None)
    devices = Device.objects.filter(patient=patient).order_by('-is_active', '-last_seen')
    notes = ClinicalNote.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')
    appointments = Appointment.objects.filter(patient=patient).select_related('doctor').order_by('-datetime')
    open_alerts = Alert.objects.filter(reading__patient=patient, status='open').select_related('reading', 'rule')

    # Latest readings for quick KPI indicators
    latest_hr = VitalReading.objects.filter(patient=patient, vital_type='heart_rate').order_by('-timestamp').first()
    latest_spo2 = VitalReading.objects.filter(patient=patient, vital_type='spo2').order_by('-timestamp').first()
    latest_sys = VitalReading.objects.filter(patient=patient, vital_type='systolic_bp').order_by('-timestamp').first()
    latest_dia = VitalReading.objects.filter(patient=patient, vital_type='diastolic_bp').order_by('-timestamp').first()
    latest_glucose = VitalReading.objects.filter(patient=patient, vital_type='blood_glucose').order_by('-timestamp').first()
    latest_temp = VitalReading.objects.filter(patient=patient, vital_type='temperature').order_by('-timestamp').first()

    note_form = ClinicalNoteForm()
    doctors = User.objects.filter(role=User.Role.DOCTOR, is_active=True).order_by('last_name', 'first_name')

    context = {
        'patient': patient,
        'profile': profile,
        'devices': devices,
        'notes': notes,
        'appointments': appointments,
        'open_alerts': open_alerts,
        'latest_hr': latest_hr,
        'latest_spo2': latest_spo2,
        'latest_sys': latest_sys,
        'latest_dia': latest_dia,
        'latest_glucose': latest_glucose,
        'latest_temp': latest_temp,
        'note_form': note_form,
        'doctors': doctors,
    }
    return render(request, 'patients/patient_detail.html', context)


@doctor_required
def add_clinical_note_view(request, patient_id):
    """Saves a new clinical note written by the attending physician."""
    if request.method != 'POST':
        return redirect('patient-detail', patient_id=patient_id)

    patient = get_object_or_404(User, id=patient_id, role=User.Role.PATIENT)
    form = ClinicalNoteForm(request.POST)

    if form.is_valid():
        note = form.save(commit=False)
        note.patient = patient
        note.doctor = request.user
        note.save()
        messages.success(request, "Clinical note successfully recorded into patient chart.")
    else:
        messages.error(request, "Could not save clinical note. Content cannot be blank.")

    return redirect('patient-detail', patient_id=patient_id)


@doctor_required
def resolve_alert_view(request, alert_id):
    """
    Standard HTML POST fallback endpoint to triage and resolve an open alert.
    (Also accessible via DRF PATCH /api/alerts/<id>/resolve/)
    """
    alert = get_object_or_404(Alert, id=alert_id)

    if request.method == 'POST':
        notes = request.POST.get('resolution_notes', '').strip()
        alert.mark_resolved(user=request.user, notes=notes)
        messages.success(
            request,
            f"Alert #{alert.id} ({alert.reading.get_vital_type_display()}) successfully resolved."
        )

    return redirect(request.META.get('HTTP_REFERER', 'doctor-dashboard'))


@patient_required
def patient_dashboard_view(request):
    """
    Personal patient portal dashboard:
    - Own vitals status & interactive trend charts
    - Own upcoming and past clinical consultations
    - Appointment booking form
    - Active alerts notifications
    """
    patient = request.user
    profile = getattr(patient, 'patient_profile', None)
    devices = Device.objects.filter(patient=patient)

    # Latest readings for each vital parameter
    latest_hr = VitalReading.objects.filter(patient=patient, vital_type='heart_rate').order_by('-timestamp').first()
    latest_spo2 = VitalReading.objects.filter(patient=patient, vital_type='spo2').order_by('-timestamp').first()
    latest_sys = VitalReading.objects.filter(patient=patient, vital_type='systolic_bp').order_by('-timestamp').first()
    latest_dia = VitalReading.objects.filter(patient=patient, vital_type='diastolic_bp').order_by('-timestamp').first()
    latest_glucose = VitalReading.objects.filter(patient=patient, vital_type='blood_glucose').order_by('-timestamp').first()
    latest_temp = VitalReading.objects.filter(patient=patient, vital_type='temperature').order_by('-timestamp').first()

    # Active alerts
    active_alerts = Alert.objects.filter(reading__patient=patient, status='open').select_related('reading', 'rule')

    # Appointments
    upcoming_appointments = Appointment.objects.filter(
        patient=patient,
        status=Appointment.Status.SCHEDULED,
        datetime__gte=timezone.now()
    ).select_related('doctor').order_by('datetime')

    past_appointments = Appointment.objects.filter(
        patient=patient
    ).exclude(
        id__in=upcoming_appointments.values_list('id', flat=True)
    ).select_related('doctor').order_by('-datetime')[:10]

    # Clinical Notes visible to patient
    notes = ClinicalNote.objects.filter(patient=patient).select_related('doctor').order_by('-created_at')[:5]

    # Available doctors for booking
    doctors = User.objects.filter(role=User.Role.DOCTOR, is_active=True).order_by('last_name', 'first_name')

    # Recent raw readings history
    recent_readings = VitalReading.objects.filter(patient=patient).select_related('device').order_by('-timestamp')[:15]

    context = {
        'patient': patient,
        'profile': profile,
        'devices': devices,
        'latest_hr': latest_hr,
        'latest_spo2': latest_spo2,
        'latest_sys': latest_sys,
        'latest_dia': latest_dia,
        'latest_glucose': latest_glucose,
        'latest_temp': latest_temp,
        'active_alerts': active_alerts,
        'upcoming_appointments': upcoming_appointments,
        'past_appointments': past_appointments,
        'notes': notes,
        'doctors': doctors,
        'recent_readings': recent_readings,
    }
    return render(request, 'patients/patient_dashboard.html', context)

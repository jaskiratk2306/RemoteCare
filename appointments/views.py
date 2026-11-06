from django.shortcuts import get_object_or_404, redirect
from django.contrib.auth.decorators import login_required
from django.contrib import messages
from django.utils.dateparse import parse_datetime
from django.utils import timezone
from .models import Appointment
from accounts.models import User


@login_required
def book_appointment_view(request):
    """
    Handles appointment booking requests:
    - Patients booking consultations with a chosen doctor
    - Doctors or Admins scheduling consultations for a patient
    """
    if request.method != 'POST':
        return redirect('home-redirect')

    doctor_id = request.POST.get('doctor')
    patient_id = request.POST.get('patient_id')
    datetime_str = request.POST.get('datetime')
    reason = request.POST.get('reason', '').strip()

    # Determine patient
    if request.user.is_patient:
        patient = request.user
    elif patient_id:
        patient = get_object_or_404(User, id=patient_id, role=User.Role.PATIENT)
    else:
        messages.error(request, "A patient must be specified for this appointment.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    # Determine doctor
    if doctor_id:
        doctor = get_object_or_404(User, id=doctor_id, role=User.Role.DOCTOR)
    elif request.user.is_doctor:
        doctor = request.user
    else:
        messages.error(request, "Please select an attending doctor.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    # Parse datetime
    if not datetime_str:
        messages.error(request, "Please provide a valid consultation date and time.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    try:
        dt = parse_datetime(datetime_str)
        if dt is None:
            raise ValueError
        # If naive, make timezone-aware
        if timezone.is_naive(dt):
            dt = timezone.make_aware(dt)
    except Exception:
        messages.error(request, "Invalid date/time format. Please choose a valid date and time.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    if dt < timezone.now():
        messages.error(request, "Appointment date and time cannot be in the past.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    if not reason:
        reason = "Routine clinical review and vital sign check-in."

    appointment = Appointment.objects.create(
        patient=patient,
        doctor=doctor,
        datetime=dt,
        status=Appointment.Status.SCHEDULED,
        reason=reason,
    )

    messages.success(
        request,
        f"Appointment successfully confirmed with Dr. {doctor.get_full_name() or doctor.username} on {dt.strftime('%b %d, %Y at %H:%M UTC')}."
    )
    return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))


@login_required
def update_appointment_status_view(request, appointment_id):
    """
    Updates appointment status: 'completed' or 'cancelled'.
    Doctors/Admins can mark completed or cancelled; Patients can cancel their scheduled appointments.
    """
    appointment = get_object_or_404(Appointment, id=appointment_id)
    user = request.user

    # Permission check
    can_modify = (
        user.is_admin_role or
        (user.is_doctor and appointment.doctor_id == user.id) or
        (user.is_patient and appointment.patient_id == user.id)
    )

    if not can_modify:
        messages.error(request, "You do not have permission to modify this appointment.")
        return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

    if request.method == 'POST':
        new_status = request.POST.get('status')
        if new_status in [Appointment.Status.COMPLETED, Appointment.Status.CANCELLED, Appointment.Status.SCHEDULED]:
            # Patients can only cancel
            if user.is_patient and new_status == Appointment.Status.COMPLETED:
                messages.error(request, "Only the attending doctor can mark a clinical consultation as completed.")
            else:
                appointment.status = new_status
                appointment.save(update_fields=['status', 'updated_at'])
                messages.success(request, f"Appointment status updated to '{appointment.get_status_display()}'.")
        else:
            messages.error(request, "Invalid appointment status specified.")

    return redirect(request.META.get('HTTP_REFERER', 'home-redirect'))

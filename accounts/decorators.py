from functools import wraps
from django.shortcuts import redirect
from django.contrib import messages
from django.core.exceptions import PermissionDenied


def doctor_required(view_func):
    """Decorator ensuring user is authenticated and has Doctor or Admin role."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not (request.user.is_doctor or request.user.is_admin_role):
            messages.error(request, "Access restricted to medical doctors and clinical administrators.")
            return redirect('patient-dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def patient_required(view_func):
    """Decorator ensuring user is authenticated and has Patient role."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_patient:
            if request.user.is_doctor:
                return redirect('doctor-dashboard')
            return redirect('admin-devices')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


def admin_required(view_func):
    """Decorator ensuring user is authenticated and has Admin role."""
    @wraps(view_func)
    def _wrapped_view(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return redirect('login')
        if not request.user.is_admin_role:
            messages.error(request, "Access restricted to system administrators.")
            if request.user.is_doctor:
                return redirect('doctor-dashboard')
            return redirect('patient-dashboard')
        return view_func(request, *args, **kwargs)
    return _wrapped_view


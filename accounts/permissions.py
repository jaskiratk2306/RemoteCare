from rest_framework import permissions


class IsAdminOrDoctorUser(permissions.BasePermission):
    """Allows access only to authenticated users with Doctor or Admin role."""
    def has_permission(self, request, view):
        user = request.user
        return bool(
            user and user.is_authenticated and (user.is_doctor or user.is_admin_role)
        )


class CanAccessPatientVitals(permissions.BasePermission):
    """
    Determines if request.user is permitted to view vitals for patient <id>:
    - Admins: permitted for all patients.
    - Doctors: permitted for all patients (or their assigned patients).
    - Patients: permitted only if their own ID matches the requested patient ID.
    """
    def has_permission(self, request, view):
        return bool(request.user and request.user.is_authenticated)

    def has_object_permission(self, request, view, obj_patient_user):
        user = request.user
        if not user or not user.is_authenticated:
            return False
        if user.is_admin_role or user.is_doctor:
            return True
        return user.id == obj_patient_user.id

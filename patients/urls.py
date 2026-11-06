from django.urls import path
from .views import (
    doctor_dashboard_view,
    patient_detail_view,
    add_clinical_note_view,
    resolve_alert_view,
    patient_dashboard_view,
)

urlpatterns = [
    path('doctor/dashboard/', doctor_dashboard_view, name='doctor-dashboard'),
    path('doctor/patient/<int:patient_id>/', patient_detail_view, name='patient-detail'),
    path('doctor/patient/<int:patient_id>/notes/add/', add_clinical_note_view, name='add-clinical-note'),
    path('doctor/alerts/<int:alert_id>/resolve/', resolve_alert_view, name='resolve-alert'),
    path('patient/dashboard/', patient_dashboard_view, name='patient-dashboard'),
]


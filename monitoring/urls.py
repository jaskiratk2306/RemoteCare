from django.urls import path
from .views import (
    VitalIngestView,
    PatientVitalsListView,
    AlertListView,
    AlertResolveView,
)

urlpatterns = [
    # Biomedical device telemetry ingestion
    path('vitals/', VitalIngestView.as_view(), name='vital-ingest'),

    # Patient vitals history & query
    path('patients/<int:patient_id>/vitals/', PatientVitalsListView.as_view(), name='patient-vitals'),

    # Alert triage and resolution
    path('alerts/', AlertListView.as_view(), name='alerts-list'),
    path('alerts/<int:alert_id>/resolve/', AlertResolveView.as_view(), name='alert-resolve'),
]

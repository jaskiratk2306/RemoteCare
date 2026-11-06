# pyrefly: ignore[missing-import]
from django.utils import timezone
from django.contrib.auth import get_user_model
from django.shortcuts import get_object_or_404
from rest_framework import status, views, generics
from rest_framework.response import Response
from rest_framework.permissions import AllowAny, IsAuthenticated
from rest_framework.pagination import PageNumberPagination

from devices.models import Device
from .models import VitalReading, Alert, AlertRule
from .serializers import (
    VitalIngestSerializer,
    VitalReadingSerializer,
    AlertSerializer,
    AlertResolveSerializer,
)
from .services import evaluate_reading
from accounts.permissions import CanAccessPatientVitals, IsAdminOrDoctorUser

User = get_user_model()


class PatientVitalsPagination(PageNumberPagination):
    page_size = 50
    page_size_query_param = 'page_size'
    max_page_size = 200


class VitalIngestView(views.APIView):
    """
    Ingestion endpoint for biomedical devices.
    Authenticated via HTTP header:
        X-API-KEY: <device_api_key>

    Request Body:
        {
            "vital_type": "heart_rate",
            "value": 78.5,
            "unit": "bpm",
            "timestamp": "2026-10-31T20:00:00Z" (optional)
        }

    Side Effects:
        1. Persists new VitalReading associated with Device & Patient
        2. Updates Device.last_seen
        3. Executes Alert Engine to evaluate thresholds and create alerts
    """
    permission_classes = [AllowAny]

    def post(self, request, *args, **kwargs):
        # Retrieve API key from custom header
        api_key = request.headers.get('X-API-KEY') or request.META.get('HTTP_X_API_KEY')

        if not api_key:
            return Response(
                {"error": "Authentication required. Missing 'X-API-KEY' header."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        # Lookup device
        try:
            device = Device.objects.select_related('patient').get(api_key=api_key)
        except Device.DoesNotExist:
            return Response(
                {"error": "Invalid API key. Device not recognized."},
                status=status.HTTP_401_UNAUTHORIZED
            )

        if not device.is_active:
            return Response(
                {"error": "Device is deactivated. Ingestion rejected."},
                status=status.HTTP_403_FORBIDDEN
            )

        serializer = VitalIngestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        reading_timestamp = data.get('timestamp') or timezone.now()

        # Save VitalReading
        reading = VitalReading.objects.create(
            device=device,
            patient=device.patient,
            vital_type=data['vital_type'],
            value=data['value'],
            unit=data['unit'],
            timestamp=reading_timestamp,
        )

        # Update Device last_seen
        device.last_seen = timezone.now()
        device.save(update_fields=['last_seen', 'updated_at'])

        # Run Alert Engine
        triggered_alerts = evaluate_reading(reading)

        return Response(
            {
                "status": "success",
                "message": "Telemetry reading ingested successfully.",
                "reading": VitalReadingSerializer(reading).data,
                "alerts_triggered": len(triggered_alerts),
                "alerts": AlertSerializer(triggered_alerts, many=True).data,
            },
            status=status.HTTP_201_CREATED
        )


class PatientVitalsListView(generics.ListAPIView):
    """
    Returns telemetry readings for a specific patient.
    Supports query parameters:
        ?type=<vital_type>
        ?from=<iso_timestamp>
        ?to=<iso_timestamp>

    Permission:
        - Admins and Doctors can view any patient's vitals.
        - Patients can only view their own vitals.
    """
    serializer_class = VitalReadingSerializer
    pagination_class = PatientVitalsPagination
    permission_classes = [IsAuthenticated, CanAccessPatientVitals]

    def get_queryset(self):
        patient_id = self.kwargs.get('patient_id')
        patient = get_object_or_404(User, id=patient_id, role=User.Role.PATIENT)

        # Object-level permission check
        self.check_object_permissions(self.request, patient)

        queryset = VitalReading.objects.filter(patient=patient).select_related('device', 'patient')

        # Filter by vital type (?type=heart_rate)
        vital_type = self.request.query_params.get('type')
        if vital_type:
            queryset = queryset.filter(vital_type=vital_type)

        # Filter by from date/time (?from=2026-10-01)
        from_time = self.request.query_params.get('from')
        if from_time:
            queryset = queryset.filter(timestamp__gte=from_time)

        # Filter by to date/time (?to=2026-10-31)
        to_time = self.request.query_params.get('to')
        if to_time:
            queryset = queryset.filter(timestamp__lte=to_time)

        return queryset.order_by('-timestamp')


class AlertListView(generics.ListAPIView):
    """
    Returns alerts filtered by status, patient_id, or severity.
    Query parameters:
        ?status=open | resolved
        ?patient_id=<id>
        ?severity=low | medium | high | critical
    """
    serializer_class = AlertSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        user = self.request.user
        queryset = Alert.objects.select_related(
            'reading', 'reading__patient', 'reading__device', 'rule', 'resolved_by'
        )

        # Patients only see alerts relating to their own vitals
        if user.is_patient:
            queryset = queryset.filter(reading__patient=user)
        # Doctors and admins can see all or filter by patient_id
        elif user.is_doctor or user.is_admin_role:
            patient_id = self.request.query_params.get('patient_id')
            if patient_id:
                queryset = queryset.filter(reading__patient_id=patient_id)

        # Status filter
        alert_status = self.request.query_params.get('status')
        if alert_status:
            queryset = queryset.filter(status=alert_status)

        # Severity filter
        severity = self.request.query_params.get('severity')
        if severity:
            queryset = queryset.filter(rule__severity=severity)

        return queryset.order_by('-created_at')


class AlertResolveView(views.APIView):
    """
    Allows a Doctor or Admin to triage and resolve an open alert.
    PATCH /api/alerts/<id>/resolve/
    Body:
        {
            "resolution_notes": "Contacted patient, instructed dosage adjustment."
        }
    """
    permission_classes = [IsAuthenticated, IsAdminOrDoctorUser]

    def patch(self, request, alert_id, *args, **kwargs):
        alert = get_object_or_404(
            Alert.objects.select_related('reading', 'reading__patient', 'rule'),
            id=alert_id
        )

        serializer = AlertResolveSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        notes = serializer.validated_data.get('resolution_notes', '')

        alert.mark_resolved(user=request.user, notes=notes)

        return Response(
            {
                "status": "success",
                "message": f"Alert #{alert.id} resolved successfully.",
                "alert": AlertSerializer(alert).data,
            },
            status=status.HTTP_200_OK
        )

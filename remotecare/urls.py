"""
URL configuration for RemoteCare project.
A Remote Patient Monitoring System for Healthcare & Biomedical Device Integration.
"""

from django.contrib import admin
from django.urls import path, include
from rest_framework.response import Response
from rest_framework.decorators import api_view, permission_classes
from rest_framework.permissions import AllowAny


@api_view(['GET'])
@permission_classes([AllowAny])
def api_root_view(request):
    """RemoteCare API Root & System Status."""
    return Response({
        "system": "RemoteCare RPM - Biomedical Device Integration Platform",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "device_vital_ingestion": "/api/vitals/ [POST] (Requires X-API-KEY)",
            "patient_vitals_history": "/api/patients/<id>/vitals/?type=&from=&to= [GET]",
            "alerts_list": "/api/alerts/?status=&patient_id=&severity= [GET]",
            "alert_resolve": "/api/alerts/<id>/resolve/ [PATCH]",
            "admin_portal": "/admin/",
        }
    })


# Custom Admin site branding
admin.site.site_header = "RemoteCare Clinical Administration"
admin.site.site_title = "RemoteCare Portal"
admin.site.index_title = "Remote Patient Monitoring & Telemetry Dashboard"

urlpatterns = [
    # Administration
    path('admin/', admin.site.urls),

    # Web UI Applications
    path('', include('accounts.urls')),
    path('', include('patients.urls')),
    path('appointments/', include('appointments.urls')),
    path('', include('devices.urls')),

    # REST APIs & Ingestion
    path('api/', include('monitoring.urls')),
    path('api/', api_root_view, name='api-root'),
    path('api-auth/', include('rest_framework.urls')),
]

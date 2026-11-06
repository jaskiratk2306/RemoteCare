from rest_framework import serializers
from .models import VitalReading, AlertRule, Alert
from devices.models import Device


class VitalIngestSerializer(serializers.Serializer):
    vital_type = serializers.ChoiceField(choices=VitalReading.VITAL_TYPE_CHOICES)
    value = serializers.FloatField()
    unit = serializers.CharField(max_length=20)
    timestamp = serializers.DateTimeField(required=False, allow_null=True)


class VitalReadingSerializer(serializers.ModelSerializer):
    device_identifier = serializers.CharField(source='device.device_id', read_only=True, default=None)
    device_type = serializers.CharField(source='device.device_type', read_only=True, default=None)
    patient_username = serializers.CharField(source='patient.username', read_only=True)
    patient_full_name = serializers.SerializerMethodField()

    class Meta:
        model = VitalReading
        fields = [
            'id',
            'device',
            'device_identifier',
            'device_type',
            'patient',
            'patient_username',
            'patient_full_name',
            'vital_type',
            'value',
            'unit',
            'timestamp',
            'created_at',
        ]
        read_only_fields = ['id', 'created_at', 'device_identifier', 'device_type', 'patient_username', 'patient_full_name']

    def get_patient_full_name(self, obj):
        return obj.patient.get_full_name() or obj.patient.username


class AlertRuleSerializer(serializers.ModelSerializer):
    class Meta:
        model = AlertRule
        fields = [
            'id',
            'vital_type',
            'min_value',
            'max_value',
            'severity',
            'is_active',
            'description',
        ]


class AlertSerializer(serializers.ModelSerializer):
    reading = VitalReadingSerializer(read_only=True)
    rule = AlertRuleSerializer(read_only=True)
    resolved_by_username = serializers.CharField(source='resolved_by.username', read_only=True, default=None)
    resolved_by_name = serializers.SerializerMethodField()

    class Meta:
        model = Alert
        fields = [
            'id',
            'reading',
            'rule',
            'status',
            'resolved_by',
            'resolved_by_username',
            'resolved_by_name',
            'resolved_at',
            'resolution_notes',
            'created_at',
        ]
        read_only_fields = ['id', 'reading', 'rule', 'resolved_by', 'resolved_at', 'created_at']

    def get_resolved_by_name(self, obj):
        if obj.resolved_by:
            return obj.resolved_by.get_full_name() or obj.resolved_by.username
        return None


class AlertResolveSerializer(serializers.Serializer):
    resolution_notes = serializers.CharField(required=False, allow_blank=True, default='')

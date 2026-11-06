import logging
from typing import List
from .models import VitalReading, AlertRule, Alert

logger = logging.getLogger(__name__)


def evaluate_reading(reading: VitalReading) -> List[Alert]:
    """
    Evaluates an ingested VitalReading against active AlertRules for that vital_type.
    Creates and returns a list of generated Alert objects if threshold rules are violated.
    """
    matching_rules = AlertRule.objects.filter(
        vital_type=reading.vital_type,
        is_active=True
    )

    created_alerts = []
    for rule in matching_rules:
        if rule.is_triggered(reading.value):
            alert = Alert.objects.create(
                reading=reading,
                rule=rule,
                status='open'
            )
            created_alerts.append(alert)
            logger.warning(
                "ALERT TRIGGERED [%s] for Patient '%s': %s = %s %s violates rule (%s to %s)",
                rule.severity.upper(),
                reading.patient.username,
                reading.vital_type,
                reading.value,
                reading.unit,
                rule.min_value,
                rule.max_value,
            )

    return created_alerts

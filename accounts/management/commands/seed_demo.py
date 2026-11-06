import datetime
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from django.utils import timezone

from patients.models import PatientProfile, ClinicalNote
from devices.models import Device
from monitoring.models import VitalReading, AlertRule, Alert
from monitoring.services import evaluate_reading
from appointments.models import Appointment

User = get_user_model()


class Command(BaseCommand):
    help = "Seeds demo data: 1 admin, 2 doctors, 5 patients, devices, alert rules, and sample vitals"

    def handle(self, *args, **options):
        self.stdout.write(self.style.NOTICE("===> Starting RemoteCare demo database seeding..."))

        # 1. Admin User
        admin_user, created = User.objects.get_or_create(
            username='admin',
            defaults={
                'email': 'admin@remotecare.local',
                'first_name': 'System',
                'last_name': 'Administrator',
                'role': User.Role.ADMIN,
                'is_staff': True,
                'is_superuser': True,
                'phone_number': '+1-800-555-0199',
            }
        )
        admin_user.set_password('AdminPassword123!')
        admin_user.role = User.Role.ADMIN
        admin_user.is_staff = True
        admin_user.is_superuser = True
        admin_user.save()
        self.stdout.write(self.style.SUCCESS(f"  [+] Admin ready: {admin_user.username} (Password: AdminPassword123!)"))

        # 2. Doctors
        doctors_data = [
            {
                'username': 'dr.chen',
                'email': 'dr.sarah.chen@remotecare.local',
                'first_name': 'Sarah',
                'last_name': 'Chen',
                'phone_number': '+1-555-0101',
            },
            {
                'username': 'dr.patel',
                'email': 'dr.marcus.patel@remotecare.local',
                'first_name': 'Marcus',
                'last_name': 'Patel',
                'phone_number': '+1-555-0102',
            },
        ]

        doctors = []
        for doc_info in doctors_data:
            doc, _ = User.objects.get_or_create(
                username=doc_info['username'],
                defaults={
                    'email': doc_info['email'],
                    'first_name': doc_info['first_name'],
                    'last_name': doc_info['last_name'],
                    'role': User.Role.DOCTOR,
                    'phone_number': doc_info['phone_number'],
                    'is_staff': True,
                }
            )
            doc.set_password('DoctorPassword123!')
            doc.role = User.Role.DOCTOR
            doc.is_staff = True
            doc.save()
            doctors.append(doc)
            self.stdout.write(self.style.SUCCESS(f"  [+] Doctor ready: Dr. {doc.get_full_name()} (Password: DoctorPassword123!)"))

        dr_chen, dr_patel = doctors[0], doctors[1]

        # 3. Patients & PatientProfiles
        patients_data = [
            {
                'username': 'patient.johndoe',
                'email': 'john.doe@example.com',
                'first_name': 'John',
                'last_name': 'Doe',
                'phone_number': '+1-555-0201',
                'age': 62,
                'gender': 'male',
                'blood_group': 'O+',
                'medical_history': 'Stage 2 Hypertension, Coronary Artery Disease. Rx Lisinopril 20mg daily.',
                'doctor': dr_chen,
                'emergency': 'Jane Doe (Wife) +1-555-0301',
            },
            {
                'username': 'patient.mariagarcia',
                'email': 'maria.garcia@example.com',
                'first_name': 'Maria',
                'last_name': 'Garcia',
                'phone_number': '+1-555-0202',
                'age': 45,
                'gender': 'female',
                'blood_group': 'A+',
                'medical_history': 'Type 2 Diabetes Mellitus with peripheral neuropathy. Rx Metformin 1000mg BID.',
                'doctor': dr_patel,
                'emergency': 'Carlos Garcia (Son) +1-555-0302',
            },
            {
                'username': 'patient.robertwilson',
                'email': 'robert.wilson@example.com',
                'first_name': 'Robert',
                'last_name': 'Wilson',
                'phone_number': '+1-555-0203',
                'age': 71,
                'gender': 'male',
                'blood_group': 'B+',
                'medical_history': 'Severe COPD with chronic hypoxemia, Atrial Fibrillation. Long term oxygen therapy.',
                'doctor': dr_chen,
                'emergency': 'Alice Wilson (Daughter) +1-555-0303',
            },
            {
                'username': 'patient.emilyzhang',
                'email': 'emily.zhang@example.com',
                'first_name': 'Emily',
                'last_name': 'Zhang',
                'phone_number': '+1-555-0204',
                'age': 29,
                'gender': 'female',
                'blood_group': 'AB-',
                'medical_history': 'Gestational hypertension and mild bronchial asthma. Rx Inhaled Budesonide.',
                'doctor': dr_patel,
                'emergency': 'Kevin Zhang (Spouse) +1-555-0304',
            },
            {
                'username': 'patient.davidmiller',
                'email': 'david.miller@example.com',
                'first_name': 'David',
                'last_name': 'Miller',
                'phone_number': '+1-555-0205',
                'age': 54,
                'gender': 'male',
                'blood_group': 'O-',
                'medical_history': 'Pre-diabetes, MetS, and Grade 1 Obesity. Lifestyle modification regimen.',
                'doctor': dr_patel,
                'emergency': 'Sarah Miller (Sister) +1-555-0305',
            },
        ]

        patients = []
        for p_info in patients_data:
            pat_user, _ = User.objects.get_or_create(
                username=p_info['username'],
                defaults={
                    'email': p_info['email'],
                    'first_name': p_info['first_name'],
                    'last_name': p_info['last_name'],
                    'role': User.Role.PATIENT,
                    'phone_number': p_info['phone_number'],
                }
            )
            pat_user.set_password('PatientPassword123!')
            pat_user.role = User.Role.PATIENT
            pat_user.save()

            profile, _ = PatientProfile.objects.update_or_create(
                user=pat_user,
                defaults={
                    'age': p_info['age'],
                    'gender': p_info['gender'],
                    'blood_group': p_info['blood_group'],
                    'medical_history': p_info['medical_history'],
                    'assigned_doctor': p_info['doctor'],
                    'emergency_contact': p_info['emergency'],
                }
            )
            patients.append(pat_user)
            self.stdout.write(self.style.SUCCESS(f"  [+] Patient ready: {pat_user.get_full_name()} (Assigned Dr. {p_info['doctor'].last_name})"))

        # 4. Alert Rules
        rules_definitions = [
            {
                'vital_type': 'heart_rate',
                'min_value': 50.0,
                'max_value': 100.0,
                'severity': 'high',
                'description': 'Heart Rate threshold (Bradycardia < 50 bpm or Tachycardia > 100 bpm)'
            },
            {
                'vital_type': 'heart_rate',
                'min_value': 40.0,
                'max_value': 130.0,
                'severity': 'critical',
                'description': 'Critical Heart Rate: Extreme Arrhythmia risk (< 40 bpm or > 130 bpm)'
            },
            {
                'vital_type': 'spo2',
                'min_value': 92.0,
                'max_value': None,
                'severity': 'critical',
                'description': 'Oxygen Saturation (SpO2) Critical Drop (< 92%)'
            },
            {
                'vital_type': 'systolic_bp',
                'min_value': None,
                'max_value': 140.0,
                'severity': 'high',
                'description': 'Stage 2 Hypertension: Systolic Blood Pressure > 140 mmHg'
            },
            {
                'vital_type': 'diastolic_bp',
                'min_value': None,
                'max_value': 90.0,
                'severity': 'medium',
                'description': 'Diastolic Hypertension: Diastolic Blood Pressure > 90 mmHg'
            },
            {
                'vital_type': 'blood_glucose',
                'min_value': None,
                'max_value': 180.0,
                'severity': 'high',
                'description': 'Hyperglycemia: Blood Glucose > 180 mg/dL'
            },
            {
                'vital_type': 'blood_glucose',
                'min_value': 70.0,
                'max_value': None,
                'severity': 'critical',
                'description': 'Hypoglycemia: Blood Glucose < 70 mg/dL'
            },
            {
                'vital_type': 'temperature',
                'min_value': None,
                'max_value': 38.3,
                'severity': 'medium',
                'description': 'Pyrexia / Fever Alert: Body Temperature > 38.3°C'
            },
        ]

        created_rules = []
        for r_def in rules_definitions:
            rule, _ = AlertRule.objects.update_or_create(
                vital_type=r_def['vital_type'],
                severity=r_def['severity'],
                defaults={
                    'min_value': r_def['min_value'],
                    'max_value': r_def['max_value'],
                    'description': r_def['description'],
                    'is_active': True,
                }
            )
            created_rules.append(rule)
        self.stdout.write(self.style.SUCCESS(f"  [+] Alert Rules configured: {len(created_rules)} active rules."))

        # 5. Biomedical Devices (covering pulse_oximeter, bp_monitor, glucometer, thermometer)
        devices_config = [
            {
                'device_id': 'DEV-POX-001',
                'device_type': Device.DeviceType.PULSE_OXIMETER,
                'patient': patients[0],  # John Doe
                'api_key': 'rc_demo_pox_johndoe_key_001',
                'model_name': 'OxiSense PulsePro 400',
            },
            {
                'device_id': 'DEV-BPM-002',
                'device_type': Device.DeviceType.BP_MONITOR,
                'patient': patients[0],  # John Doe
                'api_key': 'rc_demo_bpm_johndoe_key_002',
                'model_name': 'CardioGuard BP Wave 3',
            },
            {
                'device_id': 'DEV-GLU-003',
                'device_type': Device.DeviceType.GLUCOMETER,
                'patient': patients[1],  # Maria Garcia
                'api_key': 'rc_demo_glu_mariagarcia_key_003',
                'model_name': 'GlucoTrack SmartBio',
            },
            {
                'device_id': 'DEV-BPM-004',
                'device_type': Device.DeviceType.BP_MONITOR,
                'patient': patients[1],  # Maria Garcia
                'api_key': 'rc_demo_bpm_mariagarcia_key_004',
                'model_name': 'CardioGuard BP Wave 3',
            },
            {
                'device_id': 'DEV-POX-005',
                'device_type': Device.DeviceType.PULSE_OXIMETER,
                'patient': patients[2],  # Robert Wilson
                'api_key': 'rc_demo_pox_robertwilson_key_005',
                'model_name': 'OxiSense PulsePro 400',
            },
            {
                'device_id': 'DEV-THM-006',
                'device_type': Device.DeviceType.THERMOMETER,
                'patient': patients[2],  # Robert Wilson
                'api_key': 'rc_demo_thm_robertwilson_key_006',
                'model_name': 'ThermoScan IR Clinical',
            },
            {
                'device_id': 'DEV-BPM-007',
                'device_type': Device.DeviceType.BP_MONITOR,
                'patient': patients[3],  # Emily Zhang
                'api_key': 'rc_demo_bpm_emilyzhang_key_007',
                'model_name': 'CardioGuard BP Wave 3',
            },
            {
                'device_id': 'DEV-POX-008',
                'device_type': Device.DeviceType.PULSE_OXIMETER,
                'patient': patients[3],  # Emily Zhang
                'api_key': 'rc_demo_pox_emilyzhang_key_008',
                'model_name': 'OxiSense PulsePro 400',
            },
            {
                'device_id': 'DEV-GLU-009',
                'device_type': Device.DeviceType.GLUCOMETER,
                'patient': patients[4],  # David Miller
                'api_key': 'rc_demo_glu_davidmiller_key_009',
                'model_name': 'GlucoTrack SmartBio',
            },
            {
                'device_id': 'DEV-THM-010',
                'device_type': Device.DeviceType.THERMOMETER,
                'patient': patients[4],  # David Miller
                'api_key': 'rc_demo_thm_davidmiller_key_010',
                'model_name': 'ThermoScan IR Clinical',
            },
        ]

        created_devices = {}
        now = timezone.now()
        for d_conf in devices_config:
            dev, _ = Device.objects.update_or_create(
                device_id=d_conf['device_id'],
                defaults={
                    'device_type': d_conf['device_type'],
                    'patient': d_conf['patient'],
                    'api_key': d_conf['api_key'],
                    'model_name': d_conf['model_name'],
                    'is_active': True,
                    'last_seen': now - datetime.timedelta(minutes=5),
                }
            )
            created_devices[d_conf['device_id']] = dev
            self.stdout.write(self.style.SUCCESS(
                f"  [+] Device ready: {dev.device_id} ({dev.get_device_type_display()}) -> API Key: {dev.api_key}"
            ))

        # 6. Sample Vital Readings with Historical Spread & Triggered Alerts
        sample_vitals_matrix = [
            # John Doe readings (Hypertension patient)
            (created_devices['DEV-BPM-002'], patients[0], 'systolic_bp', 128.0, 'mmHg', 180),
            (created_devices['DEV-BPM-002'], patients[0], 'diastolic_bp', 82.0, 'mmHg', 180),
            (created_devices['DEV-POX-001'], patients[0], 'heart_rate', 74.0, 'bpm', 120),
            (created_devices['DEV-POX-001'], patients[0], 'spo2', 97.0, '%', 120),
            # Spiked reading: High blood pressure (Triggers alert!)
            (created_devices['DEV-BPM-002'], patients[0], 'systolic_bp', 152.0, 'mmHg', 45),
            (created_devices['DEV-BPM-002'], patients[0], 'diastolic_bp', 96.0, 'mmHg', 45),
            (created_devices['DEV-POX-001'], patients[0], 'heart_rate', 104.0, 'bpm', 15),

            # Maria Garcia readings (Diabetes patient)
            (created_devices['DEV-GLU-003'], patients[1], 'blood_glucose', 118.0, 'mg/dL', 240),
            (created_devices['DEV-BPM-004'], patients[1], 'systolic_bp', 122.0, 'mmHg', 190),
            (created_devices['DEV-BPM-004'], patients[1], 'diastolic_bp', 78.0, 'mmHg', 190),
            # Spiked reading: Hyperglycemia (Triggers alert!)
            (created_devices['DEV-GLU-003'], patients[1], 'blood_glucose', 215.0, 'mg/dL', 60),
            (created_devices['DEV-GLU-003'], patients[1], 'blood_glucose', 135.0, 'mg/dL', 10),

            # Robert Wilson readings (COPD patient)
            (created_devices['DEV-POX-005'], patients[2], 'spo2', 94.0, '%', 300),
            (created_devices['DEV-POX-005'], patients[2], 'heart_rate', 86.0, 'bpm', 300),
            (created_devices['DEV-THM-006'], patients[2], 'temperature', 36.8, '°C', 200),
            # Spiked reading: Critical low SpO2 (Triggers alert!)
            (created_devices['DEV-POX-005'], patients[2], 'spo2', 88.5, '%', 30),
            (created_devices['DEV-POX-005'], patients[2], 'heart_rate', 112.0, 'bpm', 30),

            # Emily Zhang readings (Gestational monitoring)
            (created_devices['DEV-BPM-007'], patients[3], 'systolic_bp', 118.0, 'mmHg', 210),
            (created_devices['DEV-BPM-007'], patients[3], 'diastolic_bp', 74.0, 'mmHg', 210),
            (created_devices['DEV-POX-008'], patients[3], 'spo2', 98.5, '%', 90),
            (created_devices['DEV-POX-008'], patients[3], 'heart_rate', 78.0, 'bpm', 90),

            # David Miller readings (Pre-diabetes / Obesity)
            (created_devices['DEV-GLU-009'], patients[4], 'blood_glucose', 105.0, 'mg/dL', 180),
            (created_devices['DEV-THM-010'], patients[4], 'temperature', 38.6, '°C', 50),  # Fever (Triggers alert!)
            (created_devices['DEV-GLU-009'], patients[4], 'blood_glucose', 112.0, 'mg/dL', 20),
        ]

        total_readings = 0
        total_alerts = 0
        for dev, pat, v_type, val, unit, mins_ago in sample_vitals_matrix:
            t_stamp = now - datetime.timedelta(minutes=mins_ago)
            reading = VitalReading.objects.create(
                device=dev,
                patient=pat,
                vital_type=v_type,
                value=val,
                unit=unit,
                timestamp=t_stamp,
            )
            total_readings += 1
            alerts = evaluate_reading(reading)
            total_alerts += len(alerts)

        self.stdout.write(self.style.SUCCESS(
            f"  [+] Ingested {total_readings} vital readings; Alert Engine generated {total_alerts} alerts."
        ))

        # Triage one of the older alerts to demo the 'resolved' state
        first_alert = Alert.objects.filter(status='open').first()
        if first_alert:
            first_alert.mark_resolved(
                user=dr_chen,
                notes="Patient contacted via telehealth call. Medication compliance confirmed and oxygen flow adjusted."
            )
            self.stdout.write(self.style.SUCCESS(f"  [+] Sample alert #{first_alert.id} resolved by Dr. Sarah Chen."))

        # 7. Clinical Notes
        ClinicalNote.objects.get_or_create(
            patient=patients[0],
            doctor=dr_chen,
            defaults={
                'note': 'Patient John Doe reports mild dizziness after morning Lisinopril. Monitored BP shows occasional spikes >150 mmHg. Scheduled follow-up in 1 week.'
            }
        )
        ClinicalNote.objects.get_or_create(
            patient=patients[1],
            doctor=dr_patel,
            defaults={
                'note': 'Post-prandial glucose spike noted (215 mg/dL). Discussed dietary adherence and carb counting with patient Maria Garcia.'
            }
        )

        # 8. Appointments
        Appointment.objects.get_or_create(
            patient=patients[0],
            doctor=dr_chen,
            datetime=now + datetime.timedelta(days=2, hours=3),
            defaults={
                'status': Appointment.Status.SCHEDULED,
                'reason': 'Hypertension management and ECG tele-consultation follow-up.',
            }
        )
        Appointment.objects.get_or_create(
            patient=patients[1],
            doctor=dr_patel,
            datetime=now + datetime.timedelta(days=3, hours=5),
            defaults={
                'status': Appointment.Status.SCHEDULED,
                'reason': 'Review continuous glucose readings and HbA1c lab evaluation.',
            }
        )

        self.stdout.write(self.style.SUCCESS("\n======================================================="))
        self.stdout.write(self.style.SUCCESS(" RemoteCare Demo Seeding Completed Successfully!"))
        self.stdout.write(self.style.SUCCESS("======================================================="))
        self.stdout.write(f"Admin User : admin / AdminPassword123!")
        self.stdout.write(f"Doctor User: dr.chen / DoctorPassword123!")
        self.stdout.write(f"Doctor User: dr.patel / DoctorPassword123!")
        self.stdout.write(f"Patient User: patient.johndoe / PatientPassword123!")
        self.stdout.write(f"Active Devices: {len(devices_config)}")
        self.stdout.write(f"Test Device API Key (Pulse Oximeter): rc_demo_pox_johndoe_key_001")
        self.stdout.write(f"Test Device API Key (BP Monitor)    : rc_demo_bpm_johndoe_key_002")
        self.stdout.write(f"Test Device API Key (Glucometer)    : rc_demo_glu_mariagarcia_key_003")
        self.stdout.write(f"Test Device API Key (Thermometer)   : rc_demo_thm_robertwilson_key_006")
        self.stdout.write(self.style.SUCCESS("=======================================================\n"))

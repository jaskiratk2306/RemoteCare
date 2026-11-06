# RemoteCare: Remote Patient Monitoring System (RPM)
### Healthcare & Biomedical Device Integration Platform

RemoteCare is a clinical-grade Remote Patient Monitoring (RPM) system built with **Django 5** and **Django REST Framework (DRF)**. It enables continuous telemetry ingestion from biomedical devices (Pulse Oximeters, Blood Pressure Monitors, Glucometers, and Clinical Thermometers), evaluates biometric thresholds in real time using an intelligent alert engine, and provides role-based access for Administrators, Doctors, and Patients.

---

## 🏥 Architecture Overview

The system is organized into modular Django apps:

- **`accounts`**: Custom User model (`accounts.User`) with strict roles: `Admin`, `Doctor`, and `Patient`, and role-based permissions.
- **`patients`**: `PatientProfile` (demographics, blood group, medical history, assigned doctor) and `ClinicalNote` (consultation and observation records).
- **`devices`**: Biomedical `Device` management with auto-generated secure API keys (`rc_dev_...`), status tracking, and `last_seen` telemetry heartbeat.
- **`monitoring`**: Telemetry ingestion engine, `VitalReading`, configurable `AlertRule` thresholds, `Alert` generation engine, and clinical triage resolution.
- **`appointments`**: Clinical consultation scheduling and lifecycle management between patients and physicians.
- **`simulator`**: Standalone medical device simulator (`device_simulator.py`) using `requests` to test live continuous telemetry streaming.

---

## 🛠️ Requirements & Technology Stack

- **Python**: 3.11+ / 3.12+
- **Django**: 5.x+
- **Django REST Framework**: 3.15+
- **Database**: SQLite3 (default for immediate development), with native PyMySQL support ready to switch to MySQL.
- **CORS Headers**: Configured for seamless frontend/client connectivity.

---

## 🚀 Quickstart & Setup

### 1. Clone & Set Up Virtual Environment

```bash
# Clone the repository and navigate into the workspace
cd HealthCare

# Create and activate virtual environment
python -m venv .venv

# On Windows (PowerShell):
.venv\Scripts\Activate.ps1
# Or if using Git Bash / Unix-like terminal:
source .venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Database Migrations

Generate and apply database migrations for all domain apps:

```bash
python manage.py makemigrations accounts patients devices monitoring appointments
python manage.py migrate
```

### 3. Seed Demo Data

Populate the database with a full clinical scenario:
- **1 Admin** user
- **2 Doctors** (Cardiology & Endocrinology)
- **5 Patients** with comprehensive profiles and assigned doctors
- **10 Biomedical Devices** covering all 4 device types with auto-generated API keys
- **8 Configured Alert Rules** (Bradycardia, Tachycardia, Hypoxemia, Hypertension, Hypoglycemia, Hyperglycemia, Fever)
- **Sample historical vitals** spanning 48 hours, including readings that trigger alerts
- **Sample Clinical Notes & Appointments**

Run:

```bash
python manage.py seed_demo
```

#### Demo Credentials:
| Role | Username | Password | Notes |
| :--- | :--- | :--- | :--- |
| **Admin** | `admin` | `AdminPassword123!` | Full admin access & staff privileges |
| **Doctor** | `dr.chen` | `DoctorPassword123!` | Dr. Sarah Chen (Cardiology) |
| **Doctor** | `dr.patel` | `DoctorPassword123!` | Dr. Marcus Patel (Endocrinology) |
| **Patient** | `patient.johndoe` | `PatientPassword123!` | Hypertension, CAD |
| **Patient** | `patient.mariagarcia` | `PatientPassword123!` | Type 2 Diabetes |
| **Patient** | `patient.robertwilson` | `PatientPassword123!` | Severe COPD |
| **Patient** | `patient.emilyzhang` | `PatientPassword123!` | Gestational monitoring |
| **Patient** | `patient.davidmiller` | `PatientPassword123!` | Pre-diabetes |

---

## 📡 REST API Documentation

### 1. Biomedical Device Telemetry Ingestion
- **URL**: `POST /api/vitals/`
- **Auth**: Header `X-API-KEY: <device_api_key>`
- **Payload**:
```json
{
  "vital_type": "heart_rate",
  "value": 115.0,
  "unit": "bpm",
  "timestamp": "2026-10-31T20:30:00Z"
}
```
- **Responses**:
  - `201 Created`: Telemetry recorded, `device.last_seen` updated, and alert engine evaluation results returned.
  - `401 Unauthorized`: Missing or invalid `X-API-KEY`.
  - `403 Forbidden`: Device is marked as deactivated (`is_active=False`).

### 2. Patient Vitals Query
- **URL**: `GET /api/patients/<id>/vitals/?type=&from=&to=`
- **Auth**: Session or Basic Authentication (Doctor, Admin, or the Patient themselves)
- **Filters**:
  - `type`: filter by vital type (`heart_rate`, `spo2`, `systolic_bp`, etc.)
  - `from`: filter by minimum ISO datetime
  - `to`: filter by maximum ISO datetime
- **Permissions**:
  - Patients can only query their own vitals.
  - Doctors and Admins can query any patient's vitals.

### 3. Alerts Listing
- **URL**: `GET /api/alerts/?status=&patient_id=&severity=`
- **Auth**: Authenticated user
- **Filters**:
  - `status`: `open` or `resolved`
  - `patient_id`: ID of patient
  - `severity`: `low`, `medium`, `high`, `critical`

### 4. Alert Triage & Resolution
- **URL**: `PATCH /api/alerts/<id>/resolve/`
- **Auth**: Doctor or Admin
- **Payload**:
```json
{
  "resolution_notes": "Prescribed medication adjustment and scheduled emergency follow-up."
}
```
- **Response**: `200 OK` with updated alert state and resolution timestamp.

---

## 📟 Device Simulator

A standalone simulator is included in `simulator/device_simulator.py`. It transmits realistic clinical telemetry to the ingestion endpoint every 3 seconds, periodically generating abnormal spikes to test the alert engine.

```bash
# Run the simulator for John Doe's Pulse Oximeter:
python simulator/device_simulator.py --api-key rc_demo_pox_johndoe_key_001

# Run for a specific device type:
python simulator/device_simulator.py --api-key rc_demo_bpm_johndoe_key_002 --device-type bp_monitor --interval 2.5
```

---

## 🗄️ Switching to MySQL

The project is preconfigured to switch from SQLite to MySQL via environment variables.

1. Create a MySQL database:
```sql
CREATE DATABASE remotecare_db CHARACTER SET utf8mb4 COLLATE utf8mb4_unicode_ci;
```

2. Create a `.env` file from `.env.example`:
```env
USE_MYSQL=True
DB_NAME=remotecare_db
DB_USER=root
DB_PASSWORD=your_password
DB_HOST=127.0.0.1
DB_PORT=3306
```

3. Run migrations on MySQL:
```bash
python manage.py migrate
python manage.py seed_demo
```

---

## 🧪 Running Automated Tests

Run the test suite verifying ingestion authentication, alert engine threshold triggers, and permission boundaries:

```bash
python manage.py test monitoring
```

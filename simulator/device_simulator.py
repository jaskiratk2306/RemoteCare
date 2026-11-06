#!/usr/bin/env python3
"""
RemoteCare Biomedical Device Telemetry Simulator
Simulates realistic medical device telemetry (Pulse Oximeters, Blood Pressure Monitors,
Glucometers, and Clinical Thermometers) sending vitals to the RemoteCare ingestion API.

Usage:
    python simulator/device_simulator.py --api-key <DEVICE_API_KEY> [--url http://127.0.0.1:8000/api/vitals/] [--interval 3]
"""

import sys
import time
import random
import argparse
import datetime
import requests


# Device telemetry profiles and realistic measurement ranges
DEVICE_PROFILES = {
    'pulse_oximeter': [
        {
            'vital_type': 'heart_rate',
            'unit': 'bpm',
            'normal_range': (65.0, 88.0),
            'spike_range': (115.0, 142.0),
            'round_digits': 0,
        },
        {
            'vital_type': 'spo2',
            'unit': '%',
            'normal_range': (95.5, 99.0),
            'spike_range': (86.0, 91.0),  # Critical hypoxemia
            'round_digits': 1,
        },
    ],
    'bp_monitor': [
        {
            'vital_type': 'systolic_bp',
            'unit': 'mmHg',
            'normal_range': (114.0, 128.0),
            'spike_range': (145.0, 168.0),  # Stage 2 hypertension
            'round_digits': 0,
        },
        {
            'vital_type': 'diastolic_bp',
            'unit': 'mmHg',
            'normal_range': (72.0, 82.0),
            'spike_range': (94.0, 102.0),
            'round_digits': 0,
        },
    ],
    'glucometer': [
        {
            'vital_type': 'blood_glucose',
            'unit': 'mg/dL',
            'normal_range': (88.0, 130.0),
            'spike_range': (195.0, 240.0),  # Hyperglycemia
            'round_digits': 1,
        },
    ],
    'thermometer': [
        {
            'vital_type': 'temperature',
            'unit': '°C',
            'normal_range': (36.4, 37.1),
            'spike_range': (38.6, 39.8),  # High fever
            'round_digits': 1,
        },
    ],
}


def send_telemetry(api_url: str, api_key: str, vital_type: str, value: float, unit: str):
    """Posts a single telemetry measurement to the RemoteCare ingestion endpoint."""
    headers = {
        'X-API-KEY': api_key,
        'Content-Type': 'application/json',
        'User-Agent': 'RemoteCare-BiomedicalSimulator/1.0',
    }
    payload = {
        'vital_type': vital_type,
        'value': value,
        'unit': unit,
        'timestamp': datetime.datetime.now(datetime.timezone.utc).isoformat(),
    }

    try:
        response = requests.post(api_url, json=payload, headers=headers, timeout=5)
        return response
    except requests.exceptions.RequestException as exc:
        return exc


def run_simulation(api_url: str, api_key: str, device_type: str, interval: float, max_count: int = None):
    print("=" * 70)
    print(" RemoteCare Biomedical Telemetry Simulator")
    print("=" * 70)
    print(f" Target Ingestion URL : {api_url}")
    print(f" Device API Key       : {api_key[:12]}...{api_key[-4:] if len(api_key) > 16 else api_key}")
    print(f" Device Mode          : {device_type.upper()}")
    print(f" Transmission Interval: {interval} seconds")
    print(f" Abnormal Spike Rate  : ~20% of readings")
    print("=" * 70)
    print("Press Ctrl+C to stop simulation.\n")

    # Select parameters to cycle through
    if device_type == 'all':
        parameters = []
        for dev_type, configs in DEVICE_PROFILES.items():
            parameters.extend([(dev_type, cfg) for cfg in configs])
    elif device_type in DEVICE_PROFILES:
        parameters = [(device_type, cfg) for cfg in DEVICE_PROFILES[device_type]]
    else:
        print(f"Error: Unknown device type '{device_type}'. Available: {list(DEVICE_PROFILES.keys())} or 'all'")
        sys.exit(1)

    counter = 0
    param_idx = 0

    try:
        while True:
            dev_name, param_cfg = parameters[param_idx]
            param_idx = (param_idx + 1) % len(parameters)
            counter += 1

            # Decide whether this reading is a normal fluctuation or an abnormal spike (1 in 5 chance)
            is_spike = (random.random() < 0.20)
            val_range = param_cfg['spike_range'] if is_spike else param_cfg['normal_range']
            raw_value = random.uniform(*val_range)
            digits = param_cfg['round_digits']
            value = round(raw_value, digits) if digits > 0 else round(raw_value)

            timestamp_str = datetime.datetime.now().strftime('%H:%M:%S')

            # Send telemetry
            res = send_telemetry(api_url, api_key, param_cfg['vital_type'], value, param_cfg['unit'])

            if isinstance(res, Exception):
                print(f"[{timestamp_str}] [FAIL] Error connecting to server: {res}")
            elif res.status_code == 201:
                res_data = res.json()
                alerts_count = res_data.get('alerts_triggered', 0)
                spike_tag = "[SPIKE]" if is_spike else "[NORMAL]"

                if alerts_count > 0:
                    alert_info = res_data.get('alerts', [{}])[0]
                    severity = alert_info.get('rule', {}).get('severity', 'ALERT').upper()
                    print(
                        f"[{timestamp_str}] #{counter:03d} {dev_name:14} | "
                        f"{param_cfg['vital_type']:15} = {value:6} {param_cfg['unit']:5} "
                        f"{spike_tag} -> HTTP 201 | *** ALERT TRIGGERED ({severity}) ***"
                    )
                else:
                    print(
                        f"[{timestamp_str}] #{counter:03d} {dev_name:14} | "
                        f"{param_cfg['vital_type']:15} = {value:6} {param_cfg['unit']:5} "
                        f"{spike_tag} -> HTTP 201 OK"
                    )
            else:
                print(
                    f"[{timestamp_str}] #{counter:03d} {dev_name:14} | "
                    f"HTTP {res.status_code} Error: {res.text}"
                )

            if max_count and counter >= max_count:
                print(f"\nCompleted {counter} simulated transmissions.")
                break

            time.sleep(interval)

    except KeyboardInterrupt:
        print("\n[Simulator stopped by user].")


def main():
    parser = argparse.ArgumentParser(
        description="RemoteCare Biomedical Device Telemetry Simulator"
    )
    parser.add_argument(
        '--url',
        type=str,
        default='http://127.0.0.1:8000/api/vitals/',
        help="RemoteCare vital readings ingestion endpoint URL."
    )
    parser.add_argument(
        '--api-key',
        type=str,
        required=True,
        help="Device API key for X-API-KEY authentication header."
    )
    parser.add_argument(
        '--device-type',
        type=str,
        default='all',
        choices=['all', 'pulse_oximeter', 'bp_monitor', 'glucometer', 'thermometer'],
        help="Biomedical device type to simulate (default: all)."
    )
    parser.add_argument(
        '--interval',
        type=float,
        default=3.0,
        help="Transmission interval in seconds (default: 3.0s)."
    )
    parser.add_argument(
        '--count',
        type=int,
        default=None,
        help="Maximum number of packets to transmit before stopping."
    )

    args = parser.parse_args()
    run_simulation(
        api_url=args.url,
        api_key=args.api_key,
        device_type=args.device_type,
        interval=args.interval,
        max_count=args.count,
    )


if __name__ == '__main__':
    main()

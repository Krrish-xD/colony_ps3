#!/usr/bin/env python3
"""
Colony PS3 — Synthetic Training Data Generator
================================================
Generates labeled training data for the ML Fusion Classifier and LSTM Anomaly Detector.

This script runs FROM THE HOST machine against live Docker containers.
Ensure the following are running:
  - All 9 microservices on colony-net (ports 8001-8009 exposed)
  - Observability stack (Prometheus:9090, Loki:3100, Jaeger:16686)
  - Locust generating baseline traffic

Usage:
    python generate_training_data.py [--samples-per-fault 50] [--output-dir ./data]
    python generate_training_data.py --dry-run   # Preview plan without executing
"""

import os
import sys
import json
import time
import argparse
import requests
from datetime import datetime, timezone
from pathlib import Path


# ─── Configuration ───────────────────────────────────────────────
LOKI_URL = os.environ.get("LOKI_URL", "http://localhost:3100")
PROMETHEUS_URL = os.environ.get("PROMETHEUS_URL", "http://localhost:9090")
JAEGER_URL = os.environ.get("JAEGER_URL", "http://localhost:16686")

# Service ports — must match v2/microservices topology
SERVICE_PORTS = {
    "frontend-service": 8001,
    "auth-service": 8002,
    "catalog-service": 8003,
    "cart-service": 8004,
    "inventory-service": 8005,
    "payment-service": 8006,
    "shipping-service": 8007,
    "recommendation-service": 8008,
    "notification-service": 8009,
}

# Fault scenarios: maps root cause labels to specific service+endpoint combos
# Multiple services per label gives diverse training data
FAULT_SCENARIOS = [
    # Crash: os._exit(1) — container dies instantly
    {"label": "crash_injection",          "service": "payment-service",       "endpoint": "/fault/crash",   "wait_after": 5},
    {"label": "crash_injection",          "service": "auth-service",          "endpoint": "/fault/crash",   "wait_after": 5},
    {"label": "crash_injection",          "service": "catalog-service",       "endpoint": "/fault/crash",   "wait_after": 5},

    # Timeout: 7s sleep — causes cascading upstream timeouts
    {"label": "upstream_timeout",         "service": "inventory-service",     "endpoint": "/fault/timeout", "wait_after": 10},
    {"label": "upstream_timeout",         "service": "catalog-service",       "endpoint": "/fault/timeout", "wait_after": 10},
    {"label": "upstream_timeout",         "service": "notification-service",  "endpoint": "/fault/timeout", "wait_after": 10},

    # Error: HTTP 500 — connection refused / internal error
    {"label": "connection_refused",       "service": "shipping-service",      "endpoint": "/fault/error",   "wait_after": 4},
    {"label": "connection_refused",       "service": "recommendation-service","endpoint": "/fault/error",   "wait_after": 4},

    # DB exhaustion (simulated via timeout on payment)
    {"label": "db_connection_exhaustion", "service": "payment-service",       "endpoint": "/fault/timeout", "wait_after": 10},

    # Memory pressure (simulated via repeated errors on cart)
    {"label": "memory_pressure",          "service": "cart-service",          "endpoint": "/fault/error",   "wait_after": 4},
]


# ─── Signal Collection ───────────────────────────────────────────

def query_loki(service: str, window_seconds: int = 15, limit: int = 50) -> list[str]:
    """Query Loki for recent log messages from a service."""
    end_ns = int(time.time() * 1e9)
    start_ns = end_ns - (window_seconds * int(1e9))

    for label_key in ["app", "service", "service_name"]:
        try:
            resp = requests.get(
                f"{LOKI_URL}/loki/api/v1/query_range",
                params={
                    "query": f'{{{label_key}="{service}"}} | json',
                    "start": str(start_ns),
                    "end": str(end_ns),
                    "limit": str(limit),
                },
                timeout=5,
            )
            if resp.status_code == 200:
                results = resp.json().get("data", {}).get("result", [])
                messages = []
                for stream in results:
                    for ts, line in stream.get("values", []):
                        try:
                            parsed = json.loads(line)
                            messages.append(parsed.get("message", line))
                        except json.JSONDecodeError:
                            messages.append(line)
                if messages:
                    return messages[:limit]
        except Exception as e:
            pass  # Try next label key

    return []


def query_prometheus(service: str, window_seconds: int = 60) -> list[list]:
    """Query Prometheus for latency metrics. Returns [[timestamp, value], ...]."""
    end_time = time.time()
    start_time = end_time - window_seconds

    # OTel metric names vary by SDK version — try multiple
    metric_queries = [
        f'http_server_duration_milliseconds_sum{{service="{service}"}}',
        f'http_server_request_duration_seconds_sum{{service="{service}"}}',
        f'http_request_duration_seconds_sum{{service="{service}"}}',
        f'http_server_duration_seconds_sum{{job="{service}"}}',
    ]

    for query in metric_queries:
        try:
            resp = requests.get(
                f"{PROMETHEUS_URL}/api/v1/query_range",
                params={"query": query, "start": str(start_time), "end": str(end_time), "step": "1"},
                timeout=5,
            )
            if resp.status_code == 200:
                results = resp.json().get("data", {}).get("result", [])
                if results:
                    return results[0].get("values", [])
        except Exception:
            pass

    return []


def query_jaeger(service: str, limit: int = 10) -> list[dict]:
    """Query Jaeger for recent traces involving a service."""
    try:
        resp = requests.get(
            f"{JAEGER_URL}/api/traces",
            params={"service": service, "limit": str(limit), "lookback": "5m"},
            timeout=5,
        )
        if resp.status_code == 200:
            spans = []
            for trace in resp.json().get("data", []):
                for span in trace.get("spans", []):
                    pid = span.get("processID", "p1")
                    svc = trace.get("processes", {}).get(pid, {}).get("serviceName", "unknown")
                    status = 200
                    for tag in span.get("tags", []):
                        if tag.get("key") in ("http.status_code", "http.response.status_code"):
                            try: status = int(tag["value"])
                            except: pass
                        elif tag.get("key") == "error" and tag.get("value"):
                            status = 500
                    spans.append({
                        "service_name": svc,
                        "operation_name": span.get("operationName", ""),
                        "duration_us": span.get("duration", 0),
                        "status_code": status,
                    })
            return spans[:50]
    except Exception:
        pass
    return []


# ─── Fault Injection ─────────────────────────────────────────────

def inject_fault(service: str, endpoint: str) -> bool:
    """Hit a service's fault endpoint from the host via localhost."""
    port = SERVICE_PORTS.get(service)
    if not port:
        return False
    try:
        requests.get(f"http://localhost:{port}{endpoint}", timeout=3)
        return True
    except (requests.exceptions.ConnectionError, requests.exceptions.ReadTimeout):
        return True  # Expected for crash/timeout
    except Exception:
        return False


# ─── Main Pipeline ───────────────────────────────────────────────

def main():
    parser = argparse.ArgumentParser(description="Generate synthetic ML training data")
    parser.add_argument("--samples-per-fault", type=int, default=50, help="Samples per fault scenario")
    parser.add_argument("--normal-samples", type=int, default=100, help="Normal operation samples")
    parser.add_argument("--output-dir", type=str, default="./data", help="Output directory")
    parser.add_argument("--dry-run", action="store_true", help="Print plan without executing")
    args = parser.parse_args()

    output_dir = Path(args.output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)

    total = len(FAULT_SCENARIOS) * args.samples_per_fault + args.normal_samples

    print(f"╔══════════════════════════════════════════════════════╗")
    print(f"║  Colony PS3 — Training Data Generator                ║")
    print(f"║  Samples: {total:<5}  Output: {str(output_dir):<25}   ║")
    print(f"╚══════════════════════════════════════════════════════╝\n")

    if args.dry_run:
        print("[DRY RUN] Plan:")
        for s in FAULT_SCENARIOS:
            print(f"  {args.samples_per_fault}x {s['label']:<30} → {s['service']}{s['endpoint']}")
        print(f"  {args.normal_samples}x {'normal_operation':<30} → (no fault)")
        return

    # Connectivity check
    print("[*] Checking services...")
    for svc, port in SERVICE_PORTS.items():
        try:
            r = requests.get(f"http://localhost:{port}/health", timeout=2)
            icon = "✅" if r.status_code == 200 else "⚠️"
        except Exception:
            icon = "❌"
        print(f"  {icon} {svc}:{port}")

    print("\n[*] Checking observability...")
    for name, url in [("Loki", f"{LOKI_URL}/ready"), ("Prometheus", f"{PROMETHEUS_URL}/-/ready"), ("Jaeger", f"{JAEGER_URL}/")]:
        try:
            icon = "✅" if requests.get(url, timeout=2).status_code == 200 else "⚠️"
        except Exception:
            icon = "❌"
        print(f"  {icon} {name}")

    print()
    input("Press ENTER to begin (ensure Locust is running)...")

    all_samples = []

    # Phase 1: Normal operation
    print(f"\n[Phase 1] Collecting {args.normal_samples} normal samples...")
    services = list(SERVICE_PORTS.keys())
    for i in range(args.normal_samples):
        svc = services[i % len(services)]
        logs = query_loki(svc, 15, 50)
        metrics = query_prometheus(svc, 60)
        traces = query_jaeger(svc, 10)
        all_samples.append({
            "label": "normal_operation", "service": svc,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "logs": logs, "metrics": metrics, "traces": traces,
        })
        if (i + 1) % 10 == 0:
            print(f"  [{i+1}/{args.normal_samples}] {svc} — logs={len(logs)} metrics={len(metrics)} traces={len(traces)}")
        time.sleep(1)

    # Phase 2: Fault injection
    for scenario in FAULT_SCENARIOS:
        label, svc, endpoint, wait = scenario["label"], scenario["service"], scenario["endpoint"], scenario["wait_after"]
        print(f"\n[Phase 2] {args.samples_per_fault}x '{label}' via {svc}{endpoint}...")

        for i in range(args.samples_per_fault):
            inject_fault(svc, endpoint)
            time.sleep(wait)

            logs = query_loki(svc, 15, 50)
            metrics = query_prometheus(svc, 60)
            traces = query_jaeger(svc, 10)
            all_samples.append({
                "label": label, "service": svc,
                "timestamp": datetime.now(timezone.utc).isoformat(),
                "logs": logs, "metrics": metrics, "traces": traces,
            })

            if (i + 1) % 10 == 0:
                print(f"  [{i+1}/{args.samples_per_fault}] logs={len(logs)} metrics={len(metrics)} traces={len(traces)}")

            # Extra wait for crash recovery
            if endpoint == "/fault/crash":
                time.sleep(15)
            else:
                time.sleep(2)

    # Save
    print(f"\n[*] Saving {len(all_samples)} samples...")
    for i, s in enumerate(all_samples):
        with open(output_dir / f"sample_{i:04d}_{s['label']}_{s['service']}.json", "w") as f:
            json.dump(s, f, indent=2)

    with open(output_dir / "dataset.json", "w") as f:
        json.dump(all_samples, f, indent=2)

    # Summary
    label_counts = {}
    for s in all_samples:
        label_counts[s["label"]] = label_counts.get(s["label"], 0) + 1

    print(f"\n{'═'*50}")
    print(f"  COMPLETE — {len(all_samples)} samples saved to {output_dir}")
    for label, count in sorted(label_counts.items()):
        print(f"  {label:<30} {count:>4}")
    print(f"{'═'*50}")


if __name__ == "__main__":
    main()

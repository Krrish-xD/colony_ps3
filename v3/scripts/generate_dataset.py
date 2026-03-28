import json
import requests
from urllib.parse import quote
from pathlib import Path

# Telemetry Endpoints
PROMETHEUS_URL = "http://localhost:9090"
LOKI_URL = "http://localhost:3100"
JAEGER_URL = "http://localhost:16686"

# Scenario Configuration
SCENARIO_ID = "cross-frontend-cart-001"
TARGET_SERVICE = "frontend"
ROOT_CAUSE_SERVICE = "cart"
ROOT_CAUSE_TYPE = "latency_spike"
TIME_WINDOW = "5m"

def query_prometheus():
    """Fetch metric features from Prometheus"""
    latency_query = f'histogram_quantile(0.95, sum(rate(http_server_duration_milliseconds_bucket{{service="{TARGET_SERVICE}"}}[{TIME_WINDOW}])) by (le))'
    error_query = f'sum(rate(http_requests_total{{service="{TARGET_SERVICE}", status=~"5.."}}[{TIME_WINDOW}])) / sum(rate(http_requests_total{{service="{TARGET_SERVICE}"}}[{TIME_WINDOW}]))'
    rps_query = f'sum(rate(http_requests_total{{service="{TARGET_SERVICE}"}}[{TIME_WINDOW}]))'

    def fetch(q):
        try:
            res = requests.get(f"{PROMETHEUS_URL}/api/v1/query?query={quote(q)}", timeout=3)
            data = res.json().get("data", {}).get("result", [])
            return float(data[0]["value"][1]) if data else 0.0
        except Exception:
            return 0.0

    return {
        "latency_ms": round(fetch(latency_query), 2),
        "error_rate": round(fetch(error_query), 4),
        "rps": round(fetch(rps_query), 2)
    }

def query_loki():
    """Fetch log counts and features from Loki"""
    error_query = f'sum(count_over_time({{service="{TARGET_SERVICE}"}} |= "error" or |= "WARN" [{TIME_WINDOW}]))'
    timeout_query = f'sum(count_over_time({{service="{TARGET_SERVICE}"}} |= "timeout" or |= "context deadline" [{TIME_WINDOW}]))'
    log_sample_query = f'{{service="{TARGET_SERVICE}"}} |~ "error|timeout"'

    def fetch_count(q):
        try:
            res = requests.get(f"{LOKI_URL}/loki/api/v1/query?query={quote(q)}", timeout=3)
            data = res.json().get("data", {}).get("result", [])
            return int(data[0]["value"][1]) if data else 0
        except Exception:
            return 0

    def fetch_sample(q):
        try:
            res = requests.get(f"{LOKI_URL}/loki/api/v1/query?query={quote(q)}&limit=1", timeout=3)
            data = res.json().get("data", {}).get("result", [])
            return data[0]["values"][0][1] if data and data[0].get("values") else ""
        except Exception:
            return ""

    error_count = fetch_count(error_query)
    timeout_count = fetch_count(timeout_query)
    
    keywords = []
    if error_count > 0: keywords.append("error")
    if timeout_count > 0: keywords.append("timeout")

    return {
        "error_count": error_count,
        "timeout_count": timeout_count,
        "keywords": keywords,
        "sample_log": fetch_sample(log_sample_query)
    }

def query_jaeger():
    """Fetch trace paths and bottlenecks from Jaeger"""
    try:
        res = requests.get(f"{JAEGER_URL}/api/traces?service={TARGET_SERVICE}&limit=1", timeout=3)
        data = res.json().get("data", [])
        if not data:
            return {"path": [], "bottleneck_service": ""}
        
        trace = data[0]
        spans = trace.get("spans", [])
        processes = trace.get("processes", {})
        
        service_path = list(set([processes.get(span["processID"], {}).get("serviceName") for span in spans if span["processID"] in processes]))
        
        if spans:
            longest_span = max(spans, key=lambda s: s.get("duration", 0))
            bottleneck_pid = longest_span.get("processID")
            bottleneck_svc = processes.get(bottleneck_pid, {}).get("serviceName", TARGET_SERVICE)
        else:
            bottleneck_svc = TARGET_SERVICE

        return {
            "path": service_path,
            "bottleneck_service": bottleneck_svc
        }
    except Exception:
        return {"path": [], "bottleneck_service": ""}

def main():
    print(f"Generating dataset entry for scenario: '{SCENARIO_ID}'...")
    
    entry = {
        "scenario_id": SCENARIO_ID,
        "target_service": TARGET_SERVICE,
        "error_type": ROOT_CAUSE_TYPE,
        "metric_features": query_prometheus(),
        "log_features": query_loki(),
        "trace": query_jaeger(),
        "root_cause_service": ROOT_CAUSE_SERVICE,
        "root_cause_type": ROOT_CAUSE_TYPE,
        "confidence_hint": "High",
        "reasoning": f"Generated from real telemetry for {TARGET_SERVICE} spanning {TIME_WINDOW} window."
    }

    # Save format
    output_dir = Path(__file__).parent.parent / "dataset"
    output_dir.mkdir(exist_ok=True)
    out_file = output_dir / "generated_dataset.json"

    with open(out_file, "w") as f:
        json.dump([entry], f, indent=2)

    print(f"Successfully generated 1 entry and saved to: {out_file}")

if __name__ == "__main__":
    main()

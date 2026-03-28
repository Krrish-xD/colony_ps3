import asyncio
import logging
import time
import os
import httpx
import json
import torch
import numpy as np
from fastapi import FastAPI, BackgroundTasks, Request
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer

from evidence_chain import build_evidence_chain
from fingerprint_store import FingerprintStore
from models.fusion_classifier import FusionClassifier, classify, ROOT_CAUSE_CLASSES
from models.lstm_detector import lstm_predict_and_check
from models.log_classifier import ZeroShotLogClassifier

logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

app = FastAPI()

# Model and Data Store Initialization
device = 'cuda' if torch.cuda.is_available() else 'cpu'
logger.info(f"Using device: {device}")

# Load sentence transformer model
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device=device)

# Load zero-shot log classifier
log_classifier = ZeroShotLogClassifier(embedding_model, device)

# Load fusion model
fusion_model = FusionClassifier()
if os.path.exists("/app/weights/fusion_model.pt"):
    fusion_model.load_state_dict(torch.load("/app/weights/fusion_model.pt", map_location=device))
fusion_model.to(device)
fusion_model.eval()

fingerprint_store = FingerprintStore()
log_embedding_cache = {}

# Constants
MONITORED_SERVICES = [
    "frontend-service", "auth-service", "catalog-service", "cart-service",
    "inventory-service", "payment-service", "shipping-service",
    "recommendation-service", "notification-service"
]

SERVICE_TOPOLOGY = {
    "frontend-service":       ["auth-service"],
    "auth-service":           ["catalog-service"],
    "catalog-service":        ["inventory-service"],
    "cart-service":           ["catalog-service"],
    "inventory-service":      [],
    "payment-service":        ["notification-service"],
    "shipping-service":       ["inventory-service"],
    "recommendation-service": ["catalog-service"],
    "notification-service":   [],
}

REVERSE_TOPOLOGY = {}
for parent, children in SERVICE_TOPOLOGY.items():
    for child in children:
        REVERSE_TOPOLOGY.setdefault(child, []).append(parent)

def compute_blast_radius(failing_service: str) -> dict:
    """BFS upstream from failing service to find all affected services."""
    affected = set()
    queue = [failing_service]
    while queue:
        current = queue.pop(0)
        for parent in REVERSE_TOPOLOGY.get(current, []):
            if parent not in affected:
                affected.add(parent)
                queue.append(parent)
    total_services = len(SERVICE_TOPOLOGY)
    return {
        "failing_service": failing_service,
        "affected_services": sorted(list(affected)),
        "affected_count": len(affected),
        "total_services": total_services,
        "affected_traffic_pct": round(len(affected) / total_services * 100, 1)
    }

# Signal Collection
async def query_loki(service: str, window_seconds: int = 15, limit: int = 50) -> list[str]:
    # Retry mechanism: 3-second micro-buffer (6 attempts x 0.5s) to bypass ingestion latency
    max_attempts = 6
    sleep_interval = 0.5

    query = f'{{app="{service}"}} | json'

    async with httpx.AsyncClient(timeout=2.0) as client:
        for attempt in range(max_attempts):
            start_time_ns = time.time_ns() - (window_seconds * 1_000_000_000)
            try:
                resp = await client.get(
                    "http://loki:3100/loki/api/v1/query_range",
                    params={"query": query, "start": str(start_time_ns), "limit": limit}
                )
                resp.raise_for_status()
                data = resp.json()

                logs = []
                results = data.get("data", {}).get("result", [])

                if results:
                    for result in results:
                        for val in result.get("values", []):
                            try:
                                log_obj = json.loads(val[1])
                                logs.append(log_obj.get("message", val[1]))
                            except json.JSONDecodeError:
                                logs.append(val[1])
                    return logs

                # If no logs found, sleep and retry
                logger.info(f"Loki query empty for {service}, retrying (attempt {attempt + 1}/{max_attempts})")
                await asyncio.sleep(sleep_interval)

            except Exception as e:
                logger.error(f"Failed querying Loki for {service}: {e}")
                await asyncio.sleep(sleep_interval)

        return []

async def query_prometheus(service: str, window_seconds: int = 60) -> list[tuple]:
    end_time = time.time()
    start_time = end_time - window_seconds
    # NOTE: Actual metric name may differ - check Prometheus after first boot
    query = f'http_server_duration_milliseconds_sum{{service="{service}"}}'

    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.get(
                "http://prometheus:9090/api/v1/query_range",
                params={"query": query, "start": str(start_time), "end": str(end_time), "step": "1s"}
            )
            resp.raise_for_status()
            data = resp.json()

            results = data.get("data", {}).get("result", [])
            if results:
                return results[0].get("values", [])
            return []
        except Exception as e:
            logger.error(f"Failed querying Prometheus for {service}: {e}")
            return []

async def query_jaeger(service: str, limit: int = 10) -> list[dict]:
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.get(f"http://jaeger:16686/api/traces?service={service}&limit={limit}")
            resp.raise_for_status()
            data = resp.json()

            spans = []
            for trace in data.get("data", []):
                for span in trace.get("spans", []):
                    # Simplified span parsing
                    process_id = span.get("processID")
                    process = trace.get("processes", {}).get(process_id, {})
                    svc_name = process.get("serviceName", "")
                    if svc_name == service:
                        duration_us = span.get("duration", 0)
                        operation_name = span.get("operationName", "")

                        # Find error tag
                        status_code = 200
                        for tag in span.get("tags", []):
                            if tag.get("key") == "error" and tag.get("value") == True:
                                status_code = 500
                            if tag.get("key") == "http.status_code":
                                status_code = tag.get("value")

                        spans.append({
                            "service_name": svc_name,
                            "operation_name": operation_name,
                            "duration_us": duration_us,
                            "status_code": status_code
                        })
            return spans
        except Exception as e:
            logger.error(f"Failed querying Jaeger for {service}: {e}")
            return []

# Feature Extraction
def embed_logs(log_messages: list[str]) -> list[float]:
    if not log_messages:
        return [0.0] * 384  # Zero vector fallback
    embeddings = embedding_model.encode(log_messages, convert_to_numpy=True)
    return embeddings.mean(axis=0).tolist()

def extract_metric_features(metric_values: list[tuple]) -> list[float]:
    """Extract 8 statistical features from time-series metric data."""
    if not metric_values:
        return [0.0] * 8
    values = np.array([float(v) for _, v in metric_values])
    return [
        float(np.mean(values)),
        float(np.std(values)),
        float(np.polyfit(range(len(values)), values, 1)[0]) if len(values) > 1 else 0.0,
        float(np.max(values) - np.min(values)),
        float(np.percentile(values, 50)),
        float(np.percentile(values, 95)),
        float(np.min(values)),
        float(np.max(values)),
    ]

def extract_trace_features(spans: list[dict]) -> list[float]:
    """Extract 6 features from trace spans."""
    if not spans:
        return [0.0] * 6
    durations = [s.get('duration_us', 0) / 1000.0 for s in spans]
    errors = [s for s in spans if isinstance(s.get('status_code'), int) and s.get('status_code', 200) >= 400]
    return [
        float(np.mean(durations)),
        len(errors) / max(len(spans), 1),
        1.0,
        float(len(errors)),
        float(len(spans)),
        float(np.max(durations)) if durations else 0.0,
    ]

# Remediation Dispatch
async def dispatch_remediation(service, root_cause, confidence, evidence, blast, elapsed_seconds):
    payload = {
        "service": service,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence_chain": evidence,
        "blast_radius": blast,
        "rca_latency_ms": round(elapsed_seconds * 1000, 1),
        "recommended_action": "restart_container" if confidence > 0.90 else "log_only",
    }

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.post("http://remediation:5001/action", json=payload)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to dispatch remediation: {e}")

    # Store fingerprint for future similarity lookups
    fingerprint_store.store(service, root_cause, confidence, log_embedding_cache.get(service, [0]*384), payload["recommended_action"])

# Background Tasks
async def run_rca_pipeline(service_name: str):
    start_time = time.time()
    logger.info(f"Starting RCA pipeline for {service_name}")

    # Step 1: Parallel signal collection
    logs, metrics, traces = await asyncio.gather(
        query_loki(service_name, window_seconds=15, limit=50),
        query_prometheus(service_name, window_seconds=60),
        query_jaeger(service_name, limit=10)
    )

    # Step 2: Feature extraction
    log_embedding = embed_logs(logs)
    log_embedding_cache[service_name] = log_embedding
    metric_features = extract_metric_features(metrics)
    trace_features = extract_trace_features(traces)

    # Step 3: Fusion classification & ML Classification Engine Call
    # TODO (Agent 2 Integration):
    # Send `logs` directly to the new Text Classification Engine API that Agent 2 is building
    # e.g., resp = await httpx.post("http://intelligence:8000/classify", json={"logs": logs})
    # root_cause, confidence = resp.json().get("root_cause"), resp.json().get("confidence")
    root_cause, confidence, all_probs = classify(log_embedding, metric_features, trace_features, fusion_model, device)

    # Step 4: Evidence chain
    evidence = build_evidence_chain(service_name, logs, metrics, traces, root_cause, confidence)

    # Step 5: Fingerprint check
    similar_incident = fingerprint_store.find_similar(log_embedding)
    if similar_incident:
        logger.info(f"Similar past incident found: {similar_incident}")

    # Step 6: Blast radius
    blast = compute_blast_radius(service_name)

    # Step 7: Dispatch to remediation
    elapsed = time.time() - start_time
    await dispatch_remediation(service_name, root_cause, confidence, evidence, blast, elapsed)
    logger.info(f"RCA Complete for {service_name} in {elapsed:.3f}s: {root_cause} (Confidence: {confidence})")

async def lstm_monitoring_loop():
    while True:
        for service in MONITORED_SERVICES:
            metrics = await query_prometheus(service, window_seconds=60)
            if len(metrics) >= 60:
                is_anomalous, deviation = lstm_predict_and_check(service, metrics)
                if is_anomalous:
                    logger.info(f"LSTM pre-alert: {service} metric deviation={deviation:.2f}σ")
                    # Optionally trigger fusion classifier here
        await asyncio.sleep(5)

@app.on_event("startup")
async def start_lstm_monitor():
    asyncio.create_task(lstm_monitoring_loop())

# Endpoints
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/incidents")
def get_incidents():
    return fingerprint_store.get_recent()

class LogBatchRequest(BaseModel):
    logs: list[str]

@app.post("/classify_logs")
def classify_logs_endpoint(request: LogBatchRequest):
    root_cause, confidence = log_classifier.classify(request.logs)
    return {
        "root_cause": root_cause,
        "confidence": round(confidence, 4)
    }

@app.post("/alert")
async def handle_alert(request: Request, background_tasks: BackgroundTasks):
    payload = await request.json()
    logger.info(f"Received alert: {payload}")

    if payload.get("status") == "firing":
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            service_name = labels.get("service") or labels.get("compose_service") or labels.get("app")
            if service_name:
                background_tasks.add_task(run_rca_pipeline, service_name)

    return {"status": "accepted"}

@app.post("/train")
async def train_model(background_tasks: BackgroundTasks):
    def run_training():
        import subprocess
        logger.info("Starting background retraining of fusion classifier...")
        try:
            subprocess.run(["python", "/app/training/train_classifier.py"], check=True)
            logger.info("Retraining completed successfully.")
            # Reload the model weights
            if os.path.exists("/app/weights/fusion_model.pt"):
                fusion_model.load_state_dict(torch.load("/app/weights/fusion_model.pt", map_location=device))
                fusion_model.eval()
                logger.info("Reloaded fusion model weights.")
        except Exception as e:
            logger.error(f"Retraining failed: {e}")

    background_tasks.add_task(run_training)
    return {"status": "retraining started in background"}


class HealthResultRequest(BaseModel):
    incident_id: int
    service: str
    was_successful: bool


@app.post("/health_result")
def receive_health_result(request: HealthResultRequest):
    """Called by the remediation engine to report whether a restart fixed the issue."""
    fingerprint_store.mark_success(request.incident_id, request.was_successful)
    logger.info(f"Health result for incident #{request.incident_id} ({request.service}): {'success' if request.was_successful else 'failed'}")
    return {"status": "recorded"}

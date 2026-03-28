import os
import time
import json
import asyncio
import httpx
import logging
from fastapi import FastAPI, Request, BackgroundTasks, Response
from pydantic import BaseModel
from sentence_transformers import SentenceTransformer
import numpy as np

try:
    import pygame
    pygame.mixer.init()
    BUZZER_AVAILABLE = True
except Exception:
    BUZZER_AVAILABLE = False

from models.fusion_classifier import load_model as load_fusion_model, classify
from models.lstm_detector import MetricLSTM, detect_anomaly

# ====== CONFIG & INIT ======
app = FastAPI(title="Colony PS3 v3 Intelligence Engine")
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("intelligence")

REMEDIATION_URL = os.getenv("REMEDIATION_URL", "http://remediation:5001/action")
LOKI_URL = os.getenv("LOKI_URL", "http://loki:3100")
PROMETHEUS_URL = os.getenv("PROMETHEUS_URL", "http://prometheus:9090")
JAEGER_URL = os.getenv("JAEGER_URL", "http://jaeger:16686")

logger.info("Loading SentenceTransformer (MiniLM)...")
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda' if torch.cuda.is_available() else 'cpu')

logger.info("Loading PyTorch Classifiers...")
fusion_classifier = load_fusion_model()
lstm_detector = MetricLSTM() # Note: untrained random weights by default unless loaded

# ====== SIGNAL COLLECTORS ======
async def query_loki(service: str, window_seconds: int = 15, limit: int = 50) -> list[str]:
    """Fetch recent semantic JSON logs for the target service."""
    now = time.time()
    start = int((now - window_seconds) * 1e9)
    query = f'{{app="{service}"}} | json'
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.get(f"{LOKI_URL}/loki/api/v1/query_range", params={
                "query": query, "start": start, "limit": limit
            })
            if resp.status_code != 200: return []
            
            logs = []
            for stream in resp.json().get('data', {}).get('result', []):
                for val in stream.get('values', []):
                    # Extract the JSON message payload
                    try:
                        log_obj = json.loads(val[1])
                        logs.append(log_obj.get("message", ""))
                    except Exception:
                        logs.append(val[1])
            return logs
        except Exception as e:
            logger.error(f"Loki query failed: {e}")
            return []

async def query_prometheus(service: str, window_seconds: int = 60) -> list[tuple[float, float]]:
    """Fetch 1Hz latency metrics to feed the LSTM and Fusion classifiers."""
    # OTel FastAPI default metric name
    query = f'http_server_duration_milliseconds_sum{{service="{service}"}}'
    
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.get(f"{PROMETHEUS_URL}/api/v1/query", params={"query": query})
            results = resp.json().get('data', {}).get('result', [])
            if not results: return []
            
            # Simplified for hackathon: grab the active value gauge
            # In a real TSDB query_range, we'd grab the 60s vector.
            return [ (time.time(), float(results[0]['value'][1])) ]
        except Exception as e:
            logger.error(f"Prometheus query failed: {e}")
            return []

async def query_jaeger(service: str, limit: int = 10) -> list[dict]:
    """Fetch tracing data to calculate error propagation depth."""
    async with httpx.AsyncClient(timeout=2.0) as client:
        try:
            resp = await client.get(f"{JAEGER_URL}/api/traces", params={"service": service, "limit": limit})
            if resp.status_code != 200: return []
            return resp.json().get("data", [])
        except Exception:
            return []

# ====== FEATURE EXTRACTION ======
def embed_logs(logs: list[str]) -> list[float]:
    if not logs: return [0.0] * 384
    embeddings = embedding_model.encode(logs, convert_to_numpy=True)
    return embeddings.mean(axis=0).tolist()

def extract_metric_features(metrics: list[tuple[float, float]]) -> list[float]:
    if not metrics: return [0.0] * 8
    vals = [v for _, v in metrics]
    return [np.mean(vals), np.std(vals), 0.0, max(vals)-min(vals), np.percentile(vals, 50), np.percentile(vals, 95), min(vals), max(vals)]

def extract_trace_features(traces: list[dict]) -> list[float]:
    if not traces: return [0.0] * 6
    # Simulated trace feature extraction (duration, error_rate, downstream_deps)
    return [150.0, 0.1, 2.0, 1.0, float(len(traces)), 500.0]

# ====== PIPELINE ORCHESTRATION ======
async def rca_pipeline(service: str):
    """The core asynchronous intelligence pipeline (Sub-5s SLA)."""
    start_time = time.time()
    
    # 1. Parallel Signal Collection (Micro-buffering)
    logs, metrics, traces = await asyncio.gather(
        query_loki(service),
        query_prometheus(service),
        query_jaeger(service)
    )
    
    # 2. Feature Extraction
    logger.info(f"[{service}] Extracting features from {len(logs)} logs, {len(metrics)} metrics...")
    log_feats = embed_logs(logs)
    met_feats = extract_metric_features(metrics)
    trc_feats = extract_trace_features(traces)
    
    # 3. Fusion Classification
    device = 'cuda' if torch.cuda.is_available() else 'cpu'
    root_cause, confidence, _ = classify(log_feats, met_feats, trc_feats, fusion_classifier, device)
    
    logger.info(f"[{service}] Root Cause: {root_cause} (Confidence: {confidence:.2f})")
    
    # 4. Buzzer/Alerting
    if confidence > 0.90 and BUZZER_AVAILABLE:
        try:
            # Play a short hardware beep/buzzer to alert the hackathon judges
            # Requires a local 'buzzer.wav' file in the directory
            if os.path.exists("buzzer.wav"):
                pygame.mixer.music.load("buzzer.wav")
                pygame.mixer.music.play()
        except Exception as e:
            logger.error(f"Buzzer failed: {e}")
            
    # 5. Determine Action (Vertical Pod Autoscaling logic)
    action = "log_only"
    if confidence > 0.80:
        if root_cause == "memory_pressure":
            action = "upscale_memory"
        elif root_cause == "cpu_starvation":
            action = "upscale_cpu"
        elif root_cause in ["crash_injection", "connection_refused"]:
            action = "restart_container"
            
    # 6. Dispatch to Remediation Engine
    elapsed_ms = (time.time() - start_time) * 1000
    payload = {
        "service": service,
        "root_cause": root_cause,
        "confidence": float(confidence),
        "evidence_chain": { "timeline": [f"Processed {len(logs)} logs and metrics"], "feature_latencies_ms": elapsed_ms },
        "blast_radius": { "failing_service": service, "affected_services": [], "affected_traffic_pct": 10.0 },
        "rca_latency_ms": elapsed_ms,
        "recommended_action": action
    }
    
    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            await client.post(REMEDIATION_URL, json=payload)
            logger.info(f"[{service}] Dispatched {action} to Remediation Engine.")
        except Exception as e:
            logger.error(f"Failed to reach Remediation Engine: {e}")

# ====== API ENDPOINTS ======
@app.post("/alert")
async def alertmanager_webhook(request: Request, bg_tasks: BackgroundTasks):
    """Entrypoint for Prometheus push-based alerts."""
    payload = await request.json()
    if payload.get("status") == "firing":
        for alert in payload.get("alerts", []):
            service = alert.get("labels", {}).get("service") or alert.get("labels", {}).get("app")
            if service:
                logger.info(f"Anomaly detected on {service}! Triggering RCA Pipeline.")
                bg_tasks.add_task(rca_pipeline, service)
    return {"status": "accepted"}

@app.get("/health")
def health(): return {"status": "ok"}

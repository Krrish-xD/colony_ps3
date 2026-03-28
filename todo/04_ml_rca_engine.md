# Task: Build the v2 ML-Powered RCA Intelligence Engine

## Context & Objective
You are operating within the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/`). This is a sub-5-second anomaly detection and auto-remediation pipeline.

The v1 intelligence engine (`/home/xd/Coding/colony_ps3/v1/intelligence/main.py`) uses hardcoded `if "timeout" in log` string matching. Your job is to replace this with a **real ML-powered Root Cause Analysis engine** using:

1. **Sentence Transformer (all-MiniLM-L6-v2)** — embeds log messages into semantic vectors for classification
2. **Lightweight LSTM** — detects metric anomalies by predicting expected values vs actual
3. **Multi-signal fusion** — combines log embeddings + metric features + trace features into a single classification

Everything runs on a single machine (i5-12H, 16GB RAM, RTX 3050 4GB VRAM, Linux) inside Docker on the `colony-net` network.

**Do NOT** modify the microservices, observability stack, or dashboard. Only build the intelligence engine.

---

## Reference Material

- v1 intelligence engine: `/home/xd/Coding/colony_ps3/v1/intelligence/main.py` — study the webhook handler structure and Alertmanager payload parsing
- v1 service logging format: logs are JSON with fields `service`, `level`, `message`, `timestamp`, `trace_id`, `error_type`

---

## Output Directory

All files MUST be written to `/home/xd/Coding/colony_ps3/v2/intelligence/`. Create this directory.

Complete file list:
```
/home/xd/Coding/colony_ps3/v2/intelligence/main.py
/home/xd/Coding/colony_ps3/v2/intelligence/models/fusion_classifier.py
/home/xd/Coding/colony_ps3/v2/intelligence/models/lstm_detector.py
/home/xd/Coding/colony_ps3/v2/intelligence/training/generate_training_data.py
/home/xd/Coding/colony_ps3/v2/intelligence/training/train_classifier.py
/home/xd/Coding/colony_ps3/v2/intelligence/training/train_lstm.py
/home/xd/Coding/colony_ps3/v2/intelligence/evidence_chain.py
/home/xd/Coding/colony_ps3/v2/intelligence/fingerprint_store.py
/home/xd/Coding/colony_ps3/v2/intelligence/requirements.txt
/home/xd/Coding/colony_ps3/v2/intelligence/Dockerfile
```

---

## Architecture Overview

```
[Alertmanager] → POST /alert (webhook)
        ↓
[Signal Collector] — parallel async queries:
   ├── Loki:       last 50 logs for the failing service         (~50ms)
   ├── Prometheus: last 60s of metrics for the failing service  (~30ms)
   └── Jaeger:     recent traces involving the failing service  (~30ms)
        ↓  (total ~80ms with async parallel)
[Feature Extraction]
   ├── Logs  → MiniLM-L6-v2 embed → mean-pooled 384-dim vector  (~5ms GPU)
   ├── Metrics → numpy stat features: [mean, std, slope, spike_mag, p50, p95, min, max] = 8 floats (~1ms)
   └── Traces → [avg_span_dur, error_span_ratio, dep_depth, downstream_failures, total_spans, max_span_dur] = 6 floats (~1ms)
        ↓
[Fusion Classifier]
   Input: concat([384 + 8 + 6]) = 398-dim vector
   Network: Linear(398→256)→ReLU→Dropout(0.3)→Linear(256→128)→ReLU→Linear(128→8)→Softmax
   Output: class probabilities over 8 root cause categories (~2ms GPU)
        ↓
[Evidence Chain Assembly]
   Stitch: metric event + log lines + trace spans → timestamped forensic report
        ↓
[Fingerprint Store]
   Compare current log embedding to past incidents via cosine similarity (SQLite)
   → "96% similar to incident #7, which was resolved by restart (4/4 success rate)"
        ↓
[Action Dispatch]
   POST → http://remediation:5001/action
   Payload: {service, root_cause, confidence, evidence_chain, recommended_action, blast_radius}
```

---

## Root Cause Categories (8 classes)

```python
ROOT_CAUSE_CLASSES = [
    "db_connection_exhaustion",     # Connection pool drained, postgres refused
    "memory_pressure",              # OOM, memory leak patterns
    "upstream_timeout",             # Downstream service timed out causing upstream cascade
    "crash_injection",              # os._exit(1) called — hard crash
    "disk_io_saturation",           # Slow disk, I/O wait patterns
    "connection_refused",           # Network unreachable, service down
    "normal_degradation",           # Slight slowdown, not critical
    "unknown"                       # Low confidence, can't classify
]
```

---

## File Specifications

### 1. `main.py` — The FastAPI Webhook Server

This is the core entry point. It receives Alertmanager webhooks and orchestrates the full RCA pipeline.

**Endpoints:**

```python
POST /alert          # Alertmanager webhook — triggers full RCA pipeline
GET  /health         # Returns {"status": "ok"}
GET  /incidents      # Returns list of recent incidents from fingerprint store
POST /train          # Triggers re-training of the fusion classifier from stored data
```

**`POST /alert` handler logic:**
1. Parse the Alertmanager payload (same format as v1 — see reference):
   ```python
   payload = await request.json()
   if payload.get("status") == "firing":
       for alert in payload["alerts"]:
           service_name = alert["labels"].get("service") or alert["labels"].get("app")
   ```
2. **DO NOT USE `asyncio.sleep(3)`** — the v1 3-second wait is eliminated in v2.
3. Launch the RCA pipeline as a background task.

**RCA Pipeline (background task):**
```python
async def run_rca_pipeline(service_name: str):
    start_time = time.time()

    # Step 1: Parallel signal collection
    logs, metrics, traces = await asyncio.gather(
        query_loki(service_name, window_seconds=15, limit=50),
        query_prometheus(service_name, window_seconds=60),
        query_jaeger(service_name, limit=10)
    )

    # Step 2: Feature extraction
    log_embedding = embed_logs(logs)            # MiniLM → 384-dim mean-pooled
    metric_features = extract_metric_features(metrics)  # 8 floats
    trace_features = extract_trace_features(traces)     # 6 floats

    # Step 3: Fusion classification
    root_cause, confidence, all_probs = classify(log_embedding, metric_features, trace_features)

    # Step 4: Evidence chain
    evidence = build_evidence_chain(service_name, logs, metrics, traces, root_cause, confidence)

    # Step 5: Fingerprint check
    similar_incident = fingerprint_store.find_similar(log_embedding)

    # Step 6: Blast radius (BFS on known topology)
    blast = compute_blast_radius(service_name)

    # Step 7: Dispatch to remediation
    elapsed = time.time() - start_time
    await dispatch_remediation(service_name, root_cause, confidence, evidence, blast, elapsed)
```

**Signal collection functions:**

`query_loki(service, window_seconds, limit)`:
- Use `httpx.AsyncClient` with 2s timeout
- Query: `GET http://loki:3100/loki/api/v1/query_range`
- LogQL: `{app="<service>"} | json` with `start` = now minus `window_seconds` (epoch nanoseconds)
- Parse results into list of log message strings
- If Loki returns no results, return empty list (don't fail — other signals still useful)

`query_prometheus(service, window_seconds)`:
- Query: `GET http://prometheus:9090/api/v1/query_range`
- PromQL: `http_server_duration_milliseconds_sum{service="<service>"}` (adjust metric name based on actual OTel output)
- Step: `1s`, range: last `window_seconds`
- Parse into list of (timestamp, value) tuples
- NOTE: Add a comment that the actual metric name may differ — check Prometheus after first boot

`query_jaeger(service, limit)`:
- Query: `GET http://jaeger:16686/api/traces?service=<service>&limit=<limit>`
- Parse into list of spans with: `service_name`, `operation_name`, `duration_us`, `status_code`

**Embedding function:**
```python
from sentence_transformers import SentenceTransformer

# Load ONCE at module level (not per request!)
embedding_model = SentenceTransformer('all-MiniLM-L6-v2', device='cuda')  # 22MB model

def embed_logs(log_messages: list[str]) -> list[float]:
    if not log_messages:
        return [0.0] * 384  # Zero vector fallback
    embeddings = embedding_model.encode(log_messages, convert_to_numpy=True)
    return embeddings.mean(axis=0).tolist()  # Mean pooling → 384-dim
```

**Feature extraction functions:**

```python
import numpy as np

def extract_metric_features(metric_values: list[tuple]) -> list[float]:
    """Extract 8 statistical features from time-series metric data."""
    if not metric_values:
        return [0.0] * 8
    values = np.array([float(v) for _, v in metric_values])
    return [
        float(np.mean(values)),
        float(np.std(values)),
        float(np.polyfit(range(len(values)), values, 1)[0]) if len(values) > 1 else 0.0,  # slope
        float(np.max(values) - np.min(values)),  # spike magnitude
        float(np.percentile(values, 50)),
        float(np.percentile(values, 95)),
        float(np.min(values)),
        float(np.max(values)),
    ]

def extract_trace_features(spans: list[dict]) -> list[float]:
    """Extract 6 features from trace spans."""
    if not spans:
        return [0.0] * 6
    durations = [s.get('duration_us', 0) / 1000.0 for s in spans]  # convert to ms
    errors = [s for s in spans if s.get('status_code', 200) >= 400]
    return [
        float(np.mean(durations)),           # avg_span_duration_ms
        len(errors) / max(len(spans), 1),    # error_span_ratio
        1.0,                                  # dependency_depth (simplified for now)
        float(len(errors)),                  # downstream_failures
        float(len(spans)),                   # total_spans
        float(np.max(durations)) if durations else 0.0,  # max_span_duration
    ]
```

---

### 2. `models/fusion_classifier.py` — The Multi-Signal Classifier

```python
import torch
import torch.nn as nn

class FusionClassifier(nn.Module):
    """
    Multi-signal fusion classifier.
    Input: concatenation of log_embedding (384) + metric_features (8) + trace_features (6) = 398
    Output: softmax probabilities over 8 root cause classes
    """
    def __init__(self, input_dim=398, num_classes=8):
        super().__init__()
        self.network = nn.Sequential(
            nn.Linear(input_dim, 256),
            nn.ReLU(),
            nn.Dropout(0.3),
            nn.Linear(256, 128),
            nn.ReLU(),
            nn.Dropout(0.2),
            nn.Linear(128, num_classes)
        )

    def forward(self, x):
        return self.network(x)
```

Also provide a `classify()` helper function in this file:
```python
def classify(log_embedding, metric_features, trace_features, model, device='cuda'):
    features = log_embedding + metric_features + trace_features  # concatenate lists
    tensor = torch.FloatTensor(features).unsqueeze(0).to(device)
    with torch.no_grad():
        logits = model(tensor)
        probs = torch.softmax(logits, dim=1)
        confidence, predicted = torch.max(probs, 1)
    return ROOT_CAUSE_CLASSES[predicted.item()], confidence.item(), probs[0].tolist()
```

The model weights file will be saved/loaded from `/app/weights/fusion_model.pt` inside the container.

---

### 3. `models/lstm_detector.py` — Metric Anomaly Detector

A lightweight LSTM that learns the normal pattern of a metric and flags deviations.

```python
class MetricLSTM(nn.Module):
    """
    Tiny LSTM for metric anomaly detection.
    Input: sequence of 60 metric values (1 per second, last 60s)
    Output: predicted next 5 values
    """
    def __init__(self, input_size=1, hidden_size=64, num_layers=2, prediction_length=5):
        super().__init__()
        self.lstm = nn.LSTM(input_size, hidden_size, num_layers, batch_first=True)
        self.fc = nn.Linear(hidden_size, prediction_length)

    def forward(self, x):
        # x shape: (batch, seq_len, 1)
        lstm_out, _ = self.lstm(x)
        prediction = self.fc(lstm_out[:, -1, :])  # Use last hidden state
        return prediction

def detect_anomaly(actual_values, predicted_values, threshold_sigma=3.0):
    """Compare actual vs predicted. If deviation > threshold standard deviations, flag anomaly."""
    residuals = np.abs(np.array(actual_values) - np.array(predicted_values))
    mean_residual = np.mean(residuals)
    std_residual = np.std(residuals) + 1e-8
    z_scores = (residuals - mean_residual) / std_residual
    # If any of the 5 predictions deviate by > 3 sigma, it's anomalous
    is_anomalous = bool(np.any(z_scores > threshold_sigma))
    max_deviation = float(np.max(z_scores))
    return is_anomalous, max_deviation
```

**How LSTM integrates with main.py:**
- Run as a **background async loop** (not triggered by Alertmanager)
- Every 5 seconds, query Prometheus for the last 60s of `http_server_duration_milliseconds` per service
- Feed into LSTM → predict next 5 values
- If anomaly detected → log it and optionally trigger the fusion classifier immediately (before Alertmanager fires)
- This is the "catches failures before they happen" feature

Add this background loop to `main.py`:
```python
@app.on_event("startup")
async def start_lstm_monitor():
    asyncio.create_task(lstm_monitoring_loop())

async def lstm_monitoring_loop():
    while True:
        for service in MONITORED_SERVICES:
            metrics = await query_prometheus(service, window_seconds=60)
            if len(metrics) >= 60:
                is_anomalous, deviation = lstm_predict_and_check(service, metrics)
                if is_anomalous:
                    logger.info(f"LSTM pre-alert: {service} metric deviation={deviation:.2f}σ")
                    # Optionally: trigger fusion classifier immediately
        await asyncio.sleep(5)
```

LSTM weights saved/loaded from `/app/weights/lstm_model.pt`.

---

### 4. `training/generate_training_data.py` — Synthetic Data Generator

This script runs AGAINST THE LIVE MICROSERVICES to generate labeled training data.

**How it works:**
1. Ensure the 9 microservices + Locust + observability stack are running
2. For each fault type, repeat 100 times:
   a. Start 1 second of normal Locust traffic
   b. Inject the specific fault (e.g., `GET http://payment-service:8006/fault/crash`)
   c. Wait 3 seconds for telemetry to propagate
   d. Collect logs from Loki, metrics from Prometheus, traces from Jaeger
   e. Save as a labeled sample
3. Also collect 100 samples of pure `normal_operation` (no fault injected)

**Fault injection plan:**
```python
FAULT_SCENARIOS = [
    {"label": "crash_injection",          "service": "payment-service",       "port": 8006, "endpoint": "/fault/crash"},
    {"label": "crash_injection",          "service": "auth-service",          "port": 8002, "endpoint": "/fault/crash"},
    {"label": "upstream_timeout",         "service": "catalog-service",       "port": 8003, "endpoint": "/fault/timeout"},
    {"label": "upstream_timeout",         "service": "inventory-service",     "port": 8005, "endpoint": "/fault/timeout"},
    {"label": "connection_refused",       "service": "shipping-service",      "port": 8007, "endpoint": "/fault/error"},
    {"label": "connection_refused",       "service": "notification-service",  "port": 8009, "endpoint": "/fault/error"},
    {"label": "db_connection_exhaustion", "service": "payment-service",       "port": 8006, "endpoint": "/fault/timeout"},
    {"label": "memory_pressure",          "service": "cart-service",          "port": 8004, "endpoint": "/fault/error"},
]
```

> NOTE: Some fault types (disk_io, memory_pressure) are mapped to existing fault endpoints with slightly different log messages. This is acceptable for v2 — real database-backed chaos comes in v3.

**Output format:** Save all samples to `/home/xd/Coding/colony_ps3/v2/intelligence/training/data/` as JSON:
```json
{
    "label": "crash_injection",
    "service": "payment-service",
    "logs": ["log message 1", "log message 2", ...],
    "metrics": [[timestamp, value], [timestamp, value], ...],
    "traces": [{"service_name": "...", "duration_us": ..., "status_code": ...}, ...]
}
```

**The script is run manually before deployment:** `python generate_training_data.py`

---

### 5. `training/train_classifier.py` — Train the Fusion Classifier

1. Load all JSON samples from `training/data/`
2. For each sample:
   - Embed log messages with MiniLM (`model.encode(logs).mean(axis=0)`)
   - Extract metric features (8 floats)
   - Extract trace features (6 floats)
   - Concatenate → 398-dim feature vector
3. Split 80/20 train/validation
4. Train `FusionClassifier` with:
   - Loss: `CrossEntropyLoss`
   - Optimizer: `Adam(lr=1e-3)`
   - Epochs: 100 (converges fast with <1000 samples)
   - Device: `cuda` if available, else `cpu`
5. Print validation accuracy
6. Save weights to `weights/fusion_model.pt`
7. Also save the `ROOT_CAUSE_CLASSES` list to `weights/classes.json`

**Expected training time:** ~30 seconds on RTX 3050.

---

### 6. `training/train_lstm.py` — Train the LSTM Detector

1. Load metric time-series from the training data (the `metrics` field from each sample)
2. Create sliding windows: input = 60 values, target = next 5 values
3. Normalize per-window (z-score normalization)
4. Train `MetricLSTM` with:
   - Loss: `MSELoss`
   - Optimizer: `Adam(lr=1e-3)`
   - Epochs: 200
   - Device: `cuda` if available, else `cpu`
5. Save weights to `weights/lstm_model.pt`

---

### 7. `evidence_chain.py` — Forensic Evidence Chain Builder

```python
def build_evidence_chain(service_name, logs, metrics, traces, root_cause, confidence):
    """
    Assembles a timestamped forensic evidence chain from all three signals.
    Returns a structured JSON object for dashboard display.
    """
    timeline = []

    # Add metric events
    if metrics:
        values = [float(v) for _, v in metrics[-10:]]  # Last 10 data points
        if values:
            spike = max(values)
            timeline.append({
                "t": "+0.0s",
                "signal": "metric",
                "event": f"P95 latency spiked to {spike:.0f}ms on {service_name}"
            })

    # Add log events (top 3 error logs)
    error_logs = [l for l in logs if "error" in l.lower()][:3]
    for i, log in enumerate(error_logs):
        timeline.append({
            "t": f"+0.{i+1}s",
            "signal": "log",
            "event": log[:200]  # Truncate long messages
        })

    # Add trace events
    if traces:
        slowest = max(traces, key=lambda s: s.get('duration_us', 0))
        dur_ms = slowest.get('duration_us', 0) / 1000
        timeline.append({
            "t": f"+0.{len(error_logs)+1}s",
            "signal": "trace",
            "event": f"Span {slowest.get('operation_name', 'unknown')}: duration={dur_ms:.0f}ms"
        })

    return {
        "service": service_name,
        "timeline": timeline,
        "classification": root_cause,
        "confidence": confidence,
    }
```

---

### 8. `fingerprint_store.py` — Anomaly Fingerprinting with SQLite

```python
import sqlite3
import json
import numpy as np
from datetime import datetime

class FingerprintStore:
    """Stores anomaly fingerprints for similarity lookup. Self-learning: tracks if past remediation worked."""

    def __init__(self, db_path="/app/data/fingerprints.db"):
        self.conn = sqlite3.connect(db_path, check_same_thread=False)
        self._create_table()

    def _create_table(self):
        self.conn.execute("""
            CREATE TABLE IF NOT EXISTS incidents (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                service TEXT,
                root_cause TEXT,
                confidence REAL,
                embedding TEXT,
                action_taken TEXT,
                was_successful INTEGER DEFAULT -1,
                created_at TEXT
            )
        """)
        self.conn.commit()

    def store(self, service, root_cause, confidence, embedding, action_taken):
        self.conn.execute(
            "INSERT INTO incidents (service, root_cause, confidence, embedding, action_taken, created_at) VALUES (?, ?, ?, ?, ?, ?)",
            (service, root_cause, confidence, json.dumps(embedding), action_taken, datetime.utcnow().isoformat())
        )
        self.conn.commit()

    def mark_success(self, incident_id, was_successful: bool):
        self.conn.execute("UPDATE incidents SET was_successful = ? WHERE id = ?", (1 if was_successful else 0, incident_id))
        self.conn.commit()

    def find_similar(self, embedding, threshold=0.85):
        """Find the most similar past incident by cosine similarity."""
        rows = self.conn.execute("SELECT id, service, root_cause, confidence, embedding, action_taken, was_successful FROM incidents ORDER BY id DESC LIMIT 100").fetchall()
        if not rows:
            return None

        query_vec = np.array(embedding)
        best_match = None
        best_sim = 0.0

        for row in rows:
            stored_vec = np.array(json.loads(row[4]))
            sim = float(np.dot(query_vec, stored_vec) / (np.linalg.norm(query_vec) * np.linalg.norm(stored_vec) + 1e-8))
            if sim > best_sim and sim > threshold:
                best_sim = sim
                success_count = self.conn.execute("SELECT COUNT(*) FROM incidents WHERE root_cause=? AND was_successful=1", (row[2],)).fetchone()[0]
                total_count = self.conn.execute("SELECT COUNT(*) FROM incidents WHERE root_cause=? AND was_successful!=-1", (row[2],)).fetchone()[0]
                best_match = {
                    "incident_id": row[0],
                    "service": row[1],
                    "root_cause": row[2],
                    "similarity": sim,
                    "action_taken": row[5],
                    "success_rate": f"{success_count}/{total_count}" if total_count > 0 else "N/A"
                }
        return best_match

    def get_recent(self, limit=20):
        rows = self.conn.execute("SELECT id, service, root_cause, confidence, action_taken, was_successful, created_at FROM incidents ORDER BY id DESC LIMIT ?", (limit,)).fetchall()
        return [{"id": r[0], "service": r[1], "root_cause": r[2], "confidence": r[3], "action": r[4], "success": r[5], "time": r[6]} for r in rows]
```

---

### 9. `requirements.txt`

```
fastapi==0.110.0
uvicorn==0.28.0
httpx==0.27.0
sentence-transformers==2.6.1
torch==2.2.1
numpy==1.26.4
scikit-learn==1.4.1
```

**Note:** `sentence-transformers` pulls in `transformers` and `tokenizers` automatically. The `all-MiniLM-L6-v2` model (22MB) will auto-download on first run.

---

### 10. `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system deps for torch
RUN apt-get update && apt-get install -y --no-install-recommends gcc && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories for model weights and fingerprint DB
RUN mkdir -p /app/weights /app/data

EXPOSE 5000

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5000"]
```

**IMPORTANT:** For GPU support, the actual deployment should use `nvidia/cuda:12.1.0-runtime-ubuntu22.04` as base image instead, with `pip install torch --index-url https://download.pytorch.org/whl/cu121`. Add this as a comment in the Dockerfile but keep `python:3.11-slim` as default for CPU-only development/testing.

---

### Blast Radius Computation

Include this in `main.py`:
```python
# The service topology (matches v2/microservices topology)
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

# Reverse topology: which services depend on X?
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
    # Count affected traffic percentage (simplified: each service = 1 unit)
    total_services = len(SERVICE_TOPOLOGY)
    return {
        "failing_service": failing_service,
        "affected_services": sorted(list(affected)),
        "affected_count": len(affected),
        "total_services": total_services,
        "affected_traffic_pct": round(len(affected) / total_services * 100, 1)
    }
```

---

### Remediation Dispatch

The dispatch function in `main.py` sends the full RCA result to the remediation engine:
```python
async def dispatch_remediation(service, root_cause, confidence, evidence, blast, elapsed_seconds):
    payload = {
        "service": service,
        "root_cause": root_cause,
        "confidence": confidence,
        "evidence_chain": evidence,
        "blast_radius": blast,
        "rca_latency_ms": round(elapsed_seconds * 1000, 1),
        "recommended_action": "restart_container" if confidence > 0.5 else "log_only",
    }

    async with httpx.AsyncClient(timeout=3.0) as client:
        try:
            resp = await client.post("http://remediation:5001/action", json=payload)
            resp.raise_for_status()
        except Exception as e:
            logger.error(f"Failed to dispatch remediation: {e}")

    # Store fingerprint for future similarity lookups
    fingerprint_store.store(service, root_cause, confidence, log_embedding_cache.get(service, [0]*384), payload["recommended_action"])
```

---

### MONITORED_SERVICES list
```python
MONITORED_SERVICES = [
    "frontend-service", "auth-service", "catalog-service", "cart-service",
    "inventory-service", "payment-service", "shipping-service",
    "recommendation-service", "notification-service"
]
```

---

## ⚠️ OUTPUT DIRECTORY — READ THIS

All code MUST be written under `/home/xd/Coding/colony_ps3/v2/intelligence/`. Not `intelligence/`, not `v2/ml/`, not anywhere else.

---

## 🔍 Mandatory 2-Pass Self-Review

### Pass 1 — Structural Correctness
- `main.py` has all 4 endpoints: `/alert`, `/health`, `/incidents`, `/train`
- The Alertmanager payload parsing matches the v1 pattern (check `payload.get("status") == "firing"`)
- MiniLM model is loaded ONCE at module level, not per-request
- `httpx.AsyncClient` with 2s timeout for all signal queries (Loki, Prometheus, Jaeger)
- FusionClassifier input_dim=398 matches actual feature dimensions (384+8+6)
- Blast radius uses the correct topology from v2 microservices
- Docker container name in compose: `intelligence` (Alertmanager references this)
- Port: 5000 in Dockerfile CMD (Alertmanager webhook points to `intelligence:5000`)

### Pass 2 — Model & Training Pipeline
- `generate_training_data.py` uses correct service ports (8001-8009)
- Training scripts save weights to `weights/` directory
- `main.py` loads weights from `/app/weights/` (the Docker COPY puts them there)
- LSTM monitoring loop runs every 5 seconds (not blocking the main event loop)
- Fingerprint store creates `/app/data/fingerprints.db` directory on startup
- `requirements.txt` includes ALL needed packages (torch, sentence-transformers, httpx, numpy, scikit-learn)
- `ROOT_CAUSE_CLASSES` list is consistent across all files that reference it

Document any fixes during each pass.

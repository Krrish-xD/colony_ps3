# Task: Bootstrap v2 9-Tier Microservice Architecture

## Context & Objective
You are operating within the `v2` directory of the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/v2/`). This project builds an autonomous self-healing infrastructure system that detects anomalies, performs root cause analysis with ML, and auto-remediates — all under 15 seconds.

Your sole responsibility is to **bootstrap the foundational 9-tier microservice architecture** inside `/home/xd/Coding/colony_ps3/v2/microservices/`. All services must be written in **Python using FastAPI**, with OpenTelemetry instrumentation and strict JSON structured logging.

**Do NOT** build the AI/ML layer, the observability stack (Prometheus/Loki/Jaeger), the dashboard, docker-compose, or any infrastructure config. Only build the 9 isolated microservices.

---

## Reference Implementation

A working v1 service exists at `/home/xd/Coding/colony_ps3/v1/services/payment-service/main.py`. Study its patterns closely. Your v2 services must follow the same structure but with improvements noted below.

Key patterns from v1 to replicate:
- OTel setup using `TracerProvider` + `MeterProvider` with OTLP HTTP exporters
- `FastAPIInstrumentor.instrument_app(app)` + `RequestsInstrumentor().instrument()`
- A `log_event()` function that prints raw JSON to stdout
- Trace ID extraction from current OTel span context

---

## The 9 Services & Their Downstream Topology

Create the following directory structure inside `/home/xd/Coding/colony_ps3/v2/microservices/`:

| # | Service Directory | Port | Downstream Target (for `/process`) |
|---|-------------------|------|-------------------------------------|
| 1 | `frontend-service` | 8001 | `http://auth-service:8002/process` |
| 2 | `auth-service` | 8002 | `http://catalog-service:8003/process` |
| 3 | `catalog-service` | 8003 | `http://inventory-service:8005/process` |
| 4 | `cart-service` | 8004 | `http://catalog-service:8003/process` |
| 5 | `inventory-service` | 8005 | *(leaf node — no downstream, just returns success)* |
| 6 | `payment-service` | 8006 | `http://notification-service:8009/process` |
| 7 | `shipping-service` | 8007 | `http://inventory-service:8005/process` |
| 8 | `recommendation-service` | 8008 | `http://catalog-service:8003/process` |
| 9 | `notification-service` | 8009 | *(leaf node — no downstream, just returns success)* |

For **EACH** service, create exactly 3 files:
- `main.py`
- `requirements.txt`
- `Dockerfile`

---

## Detailed Specifications

### 1. `requirements.txt` (identical for all 9 services)

```
fastapi==0.110.0
uvicorn==0.28.0
requests==2.31.0
opentelemetry-distro==0.44b0
opentelemetry-exporter-otlp==1.23.0
opentelemetry-instrumentation-fastapi==0.44b0
opentelemetry-instrumentation-requests==0.44b0
```

### 2. `Dockerfile` (per-service, only the port number changes)

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE <SERVICE_PORT>

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "<SERVICE_PORT>"]
```

Replace `<SERVICE_PORT>` with the specific port for each service (8001-8009). The CMD **must** bind to the service-specific port, not 8080.

### 3. `main.py` — Full Specification

Every `main.py` must contain ALL of the following sections:

#### A. Imports & Configuration
```python
import os
import sys
import json
import time
import requests
import datetime
from fastapi import FastAPI, Request, Response
from fastapi.responses import JSONResponse

from opentelemetry import trace
from opentelemetry import metrics
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.exporter.otlp.proto.http.metric_exporter import OTLPMetricExporter
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.sdk.metrics import MeterProvider
from opentelemetry.sdk.metrics.export import PeriodicExportingMetricReader
from opentelemetry.sdk.resources import Resource
from opentelemetry.semconv.resource import ResourceAttributes
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor
```

Configuration variables:
```python
SERVICE_NAME = os.getenv("SERVICE_NAME", "<service-name>")       # e.g. "frontend-service"
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "<downstream-url>") # e.g. "http://auth-service:8002"
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")
```

For leaf nodes (`inventory-service`, `notification-service`), set `DOWNSTREAM_URL` default to `""` (empty string).

#### B. OpenTelemetry Setup (identical for all services)
```python
resource = Resource(attributes={
    ResourceAttributes.SERVICE_NAME: SERVICE_NAME
})

# Traces
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
otlp_trace_exporter = OTLPSpanExporter(endpoint=f"{OTLP_ENDPOINT}/v1/traces")
span_processor = BatchSpanProcessor(otlp_trace_exporter)
tracer_provider.add_span_processor(span_processor)

# Metrics
otlp_metric_exporter = OTLPMetricExporter(endpoint=f"{OTLP_ENDPOINT}/v1/metrics")
metric_reader = PeriodicExportingMetricReader(otlp_metric_exporter)
meter_provider = MeterProvider(resource=resource, metric_readers=[metric_reader])
metrics.set_meter_provider(meter_provider)

tracer = trace.get_tracer(__name__)
meter = metrics.get_meter(__name__)
```

#### C. FastAPI App + Instrumentation
```python
app = FastAPI(title=SERVICE_NAME)
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()
```

#### D. Strict JSON Logger (Critical for ML Pipeline)
This is the most important function. Our downstream ML Sentence Classifier depends on this exact schema. The `error_type` field must ALWAYS be present (empty string if no error).

```python
def log_event(level, message, error_type=""):
    current_span = trace.get_current_span()
    trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span and current_span.get_span_context().is_valid else ""

    log_data = {
        "service": SERVICE_NAME,
        "level": level,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "error_type": error_type
    }
    print(json.dumps(log_data), flush=True)
```

#### E. Mandatory Endpoints (ALL 5 required in every service)

```python
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/process")
def process():
    log_event("info", f"{SERVICE_NAME} received request. Processing and forwarding downstream.")
    if DOWNSTREAM_URL:
        try:
            response = requests.get(f"{DOWNSTREAM_URL}/process", timeout=10)
            response.raise_for_status()
            log_event("info", f"Downstream call to {DOWNSTREAM_URL} succeeded with status {response.status_code}.")
            return {"service": SERVICE_NAME, "downstream": response.json()}
        except requests.exceptions.ConnectionError as e:
            log_event("error", f"Downstream target {DOWNSTREAM_URL} refused connection. Network unreachable.", error_type="ConnectionError")
            return JSONResponse(status_code=502, content={"error": "Downstream connection refused"})
        except requests.exceptions.Timeout as e:
            log_event("error", f"Downstream target {DOWNSTREAM_URL} timed out after 10 seconds. Service unresponsive.", error_type="TimeoutError")
            return JSONResponse(status_code=504, content={"error": "Downstream timeout"})
        except Exception as e:
            log_event("error", f"Downstream call to {DOWNSTREAM_URL} failed unexpectedly: {str(e)}", error_type=type(e).__name__)
            return JSONResponse(status_code=500, content={"error": "Downstream call failed"})
    else:
        log_event("info", f"{SERVICE_NAME} is a leaf node. Processing complete.")
        return {"service": SERVICE_NAME, "status": "completed"}

@app.get("/fault/crash")
def fault_crash():
    log_event("error", f"{SERVICE_NAME} received crash injection. Process terminating immediately.", error_type="CrashInjection")
    os._exit(1)

@app.get("/fault/timeout")
def fault_timeout():
    log_event("warning", f"{SERVICE_NAME} received timeout injection. Sleeping for 7 seconds to simulate unresponsive state.", error_type="TimeoutInjection")
    time.sleep(7)
    log_event("info", f"{SERVICE_NAME} timeout injection complete. Resuming normal operation.")
    return {"status": "timeout_finished"}

@app.get("/fault/error")
def fault_error():
    log_event("error", f"{SERVICE_NAME} received error injection. Returning HTTP 500 Internal Server Error.", error_type="ErrorInjection")
    return JSONResponse(status_code=500, content={"error": "Simulated internal server error"})
```

**IMPORTANT:** The error log messages must be **semantic and descriptive narratives**, not terse. They will be embedded by a Sentence Transformer for ML classification. Write them as if explaining the failure to a junior engineer.

---

## Final Checklist Before Completing

- [ ] All 9 directories exist under `/home/xd/Coding/colony_ps3/v2/microservices/`
- [ ] Each directory has exactly `main.py`, `requirements.txt`, `Dockerfile`
- [ ] Each `main.py` has all 5 endpoints: `/health`, `/process`, `/fault/crash`, `/fault/timeout`, `/fault/error`
- [ ] Each `Dockerfile` exposes and binds to the correct service-specific port (8001-8009)
- [ ] `DOWNSTREAM_URL` defaults are correct per the topology table
- [ ] `SERVICE_NAME` defaults match the directory name exactly
- [ ] `log_event()` always includes the `error_type` field (empty string when no error)
- [ ] The `/process` endpoint catches `ConnectionError` and `Timeout` separately with distinct log messages
- [ ] No raw stack traces leak to stdout — all errors go through `log_event()`

---

## ⚠️ OUTPUT DIRECTORY — READ THIS

All code MUST be written under `/home/xd/Coding/colony_ps3/v2/microservices/`. Not `v2/services/`, not `services/`, not anywhere else. The full path for each service is:
```
/home/xd/Coding/colony_ps3/v2/microservices/frontend-service/main.py
/home/xd/Coding/colony_ps3/v2/microservices/auth-service/main.py
... etc
```

---

## 🔍 Mandatory 2-Pass Self-Review

After generating all 27 files, you MUST perform two review passes before declaring the task complete:

### Pass 1 — Structural Correctness
Go back and re-read every `main.py`, `Dockerfile`, and `requirements.txt` you just wrote. Verify:
- Every `SERVICE_NAME` default matches its directory name exactly (e.g., `frontend-service`, not `frontend`)
- Every `DOWNSTREAM_URL` default matches the topology table above (correct hostname AND port)
- Every `Dockerfile` EXPOSE and CMD port matches the service's assigned port (8001-8009)
- Leaf nodes (`inventory-service`, `notification-service`) have `DOWNSTREAM_URL` defaulting to `""`
- All 5 endpoints exist in every service (`/health`, `/process`, `/fault/crash`, `/fault/timeout`, `/fault/error`)

### Pass 2 — ML Log Quality
Re-read every `log_event()` call across all 9 services. Verify:
- The `error_type` field is ALWAYS present (empty string `""` for non-error events, a class name like `"ConnectionError"` for errors)
- Log messages are **semantic narratives**, not terse codes. Bad: `"timeout"`. Good: `"Downstream target auth-service:8002 timed out after 10 seconds. Service unresponsive."`
- No `print()` or `logging.*` calls exist outside of the `log_event()` function — all output must go through the structured JSON logger

Document any fixes you make during each pass.

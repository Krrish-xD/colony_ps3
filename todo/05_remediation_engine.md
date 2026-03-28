# Task: Build the v2 Auto-Remediation Engine

## Context & Objective
You are operating within the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/`). This is a sub-5-second anomaly detection and auto-remediation pipeline running entirely on a single machine (i5-12H, RTX 3050, Linux).

The v1 remediation engine (`/home/xd/Coding/colony_ps3/v1/remediation/main.py`) does a blind Docker restart with a 30s cooldown. Your v2 upgrade adds:
1. **Confidence-gated remediation** with severity flagging
2. **Instant container kill** (`docker restart -t 0`) for zero shutdown wait
3. **Post-restart health verification** (poll `/health` to confirm fix worked)
4. **Rich event streaming** to the dashboard via SSE with timing data
5. **Incident lifecycle tracking** (detection → RCA → remediation → verification → resolved)

Everything runs on the same Docker `colony-net` network.

**Do NOT** modify the microservices, observability stack, or intelligence engine. Only build the remediation engine.

---

## Reference Material

- v1 remediation engine: `/home/xd/Coding/colony_ps3/v1/remediation/main.py` — study the Docker SDK usage, cooldown cache pattern, and dashboard push
- v2 intelligence engine payload: the RCA engine at `intelligence:5000` POSTs the following to this remediation engine:
  ```json
  {
      "service": "payment-service",
      "root_cause": "db_connection_exhaustion",
      "confidence": 0.94,
      "evidence_chain": { "timeline": [...], "classification": "...", "confidence": 0.94 },
      "blast_radius": { "failing_service": "...", "affected_services": [...], "affected_traffic_pct": 34 },
      "rca_latency_ms": 95.2,
      "recommended_action": "restart_container"
  }
  ```

---

## Output Directory

All files MUST be written to `/home/xd/Coding/colony_ps3/v2/remediation/`. Create this directory.

Complete file list:
```
/home/xd/Coding/colony_ps3/v2/remediation/main.py
/home/xd/Coding/colony_ps3/v2/remediation/requirements.txt
/home/xd/Coding/colony_ps3/v2/remediation/Dockerfile
```

---

## Port Assignment

The remediation engine runs on port **5001**.
- Intelligence/RCA engine: `intelligence:5000`
- Remediation engine: `remediation:5001`
- Dashboard: `dashboard:3000`

---

## File 1: `main.py`

### Imports & Setup

```python
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import docker
import time
import httpx
import asyncio
import os
import json
from datetime import datetime
```

Docker client loaded at module level:
```python
client = docker.from_env()
```

### Data Models

```python
class RemediationRequest(BaseModel):
    service: str
    root_cause: str
    confidence: float
    evidence_chain: dict = {}
    blast_radius: dict = {}
    rca_latency_ms: float = 0.0
    recommended_action: str = "restart_container"

class IncidentRecord(BaseModel):
    id: int
    service: str
    root_cause: str
    confidence: float
    confidence_tier: str          # "high" | "medium" | "low"
    action_taken: str
    restart_duration_ms: float
    health_verified: bool
    total_pipeline_ms: float      # detection → fully resolved
    timestamp: str
```

### In-Memory State

```python
COOLDOWN_CACHE = {}          # {service_name: last_restart_epoch}
COOLDOWN_SECONDS = 30

INCIDENT_LOG = []            # List of IncidentRecord dicts
INCIDENT_COUNTER = 0

DASHBOARD_SSE_URL = os.environ.get("DASHBOARD_URL", "http://dashboard:3000/api/events")
```

### Endpoints

```python
POST /action          # Main endpoint — receives RCA payload, executes remediation
GET  /health          # Returns {"status": "ok"}
GET  /incidents       # Returns INCIDENT_LOG (last 50 incidents)
GET  /cooldowns       # Returns current COOLDOWN_CACHE state
```

### `POST /action` Handler Logic

```python
@app.post("/action")
async def handle_action(request: RemediationRequest, background_tasks: BackgroundTasks):
    current_time = time.time()

    # 1. Cooldown check
    last_restart = COOLDOWN_CACHE.get(request.service, 0)
    if current_time - last_restart < COOLDOWN_SECONDS:
        remaining = COOLDOWN_SECONDS - (current_time - last_restart)
        return {"status": "ignored", "reason": "cooldown", "remaining_seconds": round(remaining, 1)}

    # 2. Confidence gating (all auto-execute, but flag severity)
    if request.confidence >= 0.9:
        confidence_tier = "high"
    elif request.confidence >= 0.5:
        confidence_tier = "medium"
    else:
        confidence_tier = "low"
        # Still execute, but mark as low confidence for dashboard warning

    # 3. Set cooldown immediately (prevent concurrent restarts)
    COOLDOWN_CACHE[request.service] = current_time

    # 4. Offload to background task for non-blocking response
    background_tasks.add_task(
        execute_remediation,
        request,
        confidence_tier,
        current_time
    )

    return {"status": "accepted", "service": request.service, "confidence_tier": confidence_tier}
```

### Background Remediation Execution

This is the core function. It performs the restart, verifies health, computes timing, and pushes the full event to the dashboard.

```python
async def execute_remediation(request: RemediationRequest, confidence_tier: str, start_time: float):
    global INCIDENT_COUNTER
    service = request.service

    # ── STEP 1: Docker Restart (instant kill) ──
    restart_start = time.time()
    restart_success = False
    try:
        container = client.containers.get(service)
        container.restart(timeout=0)    # -t 0: kill immediately, no graceful shutdown
        restart_success = True
    except docker.errors.NotFound:
        # Container name might differ from service name in compose
        # Try with project prefix pattern: colony_ps3-payment-service-1
        try:
            containers = client.containers.list(all=True, filters={"name": service})
            if containers:
                containers[0].restart(timeout=0)
                restart_success = True
        except Exception as e:
            print(f"Failed to restart {service}: {e}")
    except Exception as e:
        print(f"Failed to restart {service}: {e}")

    restart_duration_ms = (time.time() - restart_start) * 1000

    # ── STEP 2: Health Verification ──
    # Poll the service's /health endpoint every 2s for up to 10s
    health_verified = False
    if restart_success:
        health_verified = await verify_health(service, max_attempts=5, interval=2.0)

    # ── STEP 3: Compute Full Pipeline Timing ──
    total_pipeline_ms = (time.time() - start_time) * 1000

    # ── STEP 4: Build Incident Record ──
    INCIDENT_COUNTER += 1
    incident = {
        "id": INCIDENT_COUNTER,
        "service": service,
        "root_cause": request.root_cause,
        "confidence": request.confidence,
        "confidence_tier": confidence_tier,
        "action_taken": "restart_container" if restart_success else "restart_failed",
        "restart_duration_ms": round(restart_duration_ms, 1),
        "health_verified": health_verified,
        "rca_latency_ms": request.rca_latency_ms,
        "total_pipeline_ms": round(total_pipeline_ms, 1),
        "blast_radius": request.blast_radius,
        "evidence_chain": request.evidence_chain,
        "timestamp": datetime.utcnow().isoformat() + "Z",
    }

    # Store in memory (keep last 50)
    INCIDENT_LOG.append(incident)
    if len(INCIDENT_LOG) > 50:
        INCIDENT_LOG.pop(0)

    # ── STEP 5: Push Event to Dashboard via SSE ──
    await push_to_dashboard(incident)

    # ── STEP 6: Notify Intelligence Engine of Health Check Result ──
    # The fingerprint store tracks if the fix worked
    await notify_intelligence_health_result(service, INCIDENT_COUNTER, health_verified)
```

### Health Verification Function

```python
async def verify_health(service: str, max_attempts: int = 5, interval: float = 2.0) -> bool:
    """
    Poll the restarted service's /health endpoint.
    Returns True if the service responds 200 within max_attempts.
    """
    # Map service name → internal port
    SERVICE_PORTS = {
        "frontend-service": 8001, "auth-service": 8002, "catalog-service": 8003,
        "cart-service": 8004, "inventory-service": 8005, "payment-service": 8006,
        "shipping-service": 8007, "recommendation-service": 8008, "notification-service": 8009,
    }
    port = SERVICE_PORTS.get(service)
    if not port:
        return False

    url = f"http://{service}:{port}/health"

    async with httpx.AsyncClient(timeout=2.0) as http:
        for attempt in range(max_attempts):
            try:
                resp = await http.get(url)
                if resp.status_code == 200:
                    return True
            except Exception:
                pass
            await asyncio.sleep(interval)
    return False
```

### Dashboard Push Function

```python
async def push_to_dashboard(incident: dict):
    """
    Push the full incident payload to the dashboard SSE endpoint.
    Includes all timing data, evidence chain, and blast radius.
    """
    dashboard_event = {
        "type": "remediation",
        "service": incident["service"],
        "action": incident["action_taken"],
        "root_cause": incident["root_cause"],
        "confidence": incident["confidence"],
        "confidence_tier": incident["confidence_tier"],
        "restart_duration_ms": incident["restart_duration_ms"],
        "rca_latency_ms": incident["rca_latency_ms"],
        "total_pipeline_ms": incident["total_pipeline_ms"],
        "health_verified": incident["health_verified"],
        "blast_radius": incident.get("blast_radius", {}),
        "evidence_chain": incident.get("evidence_chain", {}),
        "timestamp": incident["timestamp"],
    }

    async with httpx.AsyncClient(timeout=1.0) as http:
        try:
            await http.post(DASHBOARD_SSE_URL, json=dashboard_event)
        except Exception:
            pass  # Never fail remediation because dashboard is down
```

### Intelligence Engine Health Callback

```python
async def notify_intelligence_health_result(service: str, incident_id: int, was_successful: bool):
    """Notify the intelligence engine so the fingerprint store can track success rate."""
    async with httpx.AsyncClient(timeout=1.0) as http:
        try:
            await http.post("http://intelligence:5000/health_result", json={
                "incident_id": incident_id,
                "service": service,
                "was_successful": was_successful
            })
        except Exception:
            pass
```

> **IMPORTANT**: The intelligence engine's `main.py` must also have a `POST /health_result` endpoint that calls `fingerprint_store.mark_success()`. Include a comment noting this dependency.

---

## File 2: `requirements.txt`

```
fastapi==0.110.0
uvicorn==0.28.0
docker==7.0.0
httpx==0.27.0
pydantic==2.6.4
```

---

## File 3: `Dockerfile`

```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY main.py .

EXPOSE 5001

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "5001"]
```

**CRITICAL**: This container MUST mount the Docker socket to restart other containers:
```yaml
# In docker-compose.yml (not created here, but document this):
volumes:
  - /var/run/docker.sock:/var/run/docker.sock:ro
```

---

## Docker Container Naming

When running under Docker Compose, container names follow the pattern `<project>-<service>-<replica>` (e.g., `colony_ps3-payment-service-1`). The `docker.containers.get(service)` call uses the **Compose service name**, NOT the container name.

The code must handle BOTH:
1. First try `client.containers.get(service)` (works if container name = service name)
2. If `NotFound`, fall back to `client.containers.list(filters={"name": service})` and restart the first match

This is already handled in the `execute_remediation` function above.

---

## ⚠️ OUTPUT DIRECTORY — READ THIS

All code MUST be written to `/home/xd/Coding/colony_ps3/v2/remediation/`. The complete file list:
```
/home/xd/Coding/colony_ps3/v2/remediation/main.py
/home/xd/Coding/colony_ps3/v2/remediation/requirements.txt
/home/xd/Coding/colony_ps3/v2/remediation/Dockerfile
```

---

## 🔍 Mandatory 2-Pass Self-Review

### Pass 1 — Structural Correctness
- Port is `5001` in both Dockerfile EXPOSE and CMD
- `docker.from_env()` is called at module level (not per-request)
- `container.restart(timeout=0)` — the `timeout=0` parameter is correct for instant kill
- `COOLDOWN_SECONDS = 30` and cooldown is set BEFORE background task runs (prevents concurrent restarts)
- Health verification uses correct service ports (8001-8009) matching the microservice topology
- All 4 endpoints exist: `/action`, `/health`, `/incidents`, `/cooldowns`
- `httpx.AsyncClient` (not `requests`) used for all async HTTP calls
- Dashboard push uses `timeout=1.0` and silently catches failures

### Pass 2 — Integration Points
- The `RemediationRequest` Pydantic model accepts ALL fields from the intelligence engine payload (service, root_cause, confidence, evidence_chain, blast_radius, rca_latency_ms, recommended_action)
- Dashboard event includes timing data: `restart_duration_ms`, `rca_latency_ms`, `total_pipeline_ms`
- `push_to_dashboard` POSTs to `http://dashboard:3000/api/events` (not the SSE read endpoint)
- `notify_intelligence_health_result` POSTs to `http://intelligence:5000/health_result` (add comment that intelligence needs this endpoint)
- Container name fallback uses `client.containers.list(filters={"name": service})` for Compose naming patterns

Document any fixes during each pass.

from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
import docker
import time
import httpx
import asyncio
import os
import json
from datetime import datetime

app = FastAPI()

client = docker.from_env()

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

COOLDOWN_CACHE = {}          # {service_name: last_restart_epoch}
COOLDOWN_SECONDS = 30

INCIDENT_LOG = []            # List of IncidentRecord dicts
INCIDENT_COUNTER = 0

DASHBOARD_SSE_URL = os.environ.get("DASHBOARD_URL", "http://dashboard:3000/api/events")


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


@app.get("/health")
def get_health():
    return {"status": "ok"}


@app.get("/incidents")
def get_incidents():
    return INCIDENT_LOG


@app.get("/cooldowns")
def get_cooldowns():
    return COOLDOWN_CACHE


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


async def notify_intelligence_health_result(service: str, incident_id: int, was_successful: bool):
    """
    Notify the intelligence engine so the fingerprint store can track success rate.
    IMPORTANT: The intelligence engine's main.py must also have a POST /health_result
    endpoint that calls fingerprint_store.mark_success().
    """
    async with httpx.AsyncClient(timeout=1.0) as http:
        try:
            await http.post("http://intelligence:5000/health_result", json={
                "incident_id": incident_id,
                "service": service,
                "was_successful": was_successful
            })
        except Exception:
            pass

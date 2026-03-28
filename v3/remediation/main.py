import docker
import time
import httpx
import logging
import asyncio
from fastapi import FastAPI, BackgroundTasks
from pydantic import BaseModel
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("remediation")

app = FastAPI(title="Colony PS3 v3 Auto-Remediation")
try:
    client = docker.from_env()
    logger.info("Docker socket connected successfully.")
except Exception as e:
    logger.error(f"Docker socket error: {e}")
    client = None

DASHBOARD_URL = "http://dashboard:3000/api/events"
COOLDOWN_CACHE = {} # service: last_action_time
COOLDOWN_SECONDS = 15 # Shorter 15s cooldown for dynamic hackathon sliding
IDLE_TRACKER = {}   # service: last_traffic_epoch for downscaling logic

class ActionPayload(BaseModel):
    service: str
    root_cause: str
    confidence: float
    recommended_action: str
    evidence_chain: dict = {}
    blast_radius: dict = {}
    rca_latency_ms: float = 0.0

async def execute_dynamic_scale(payload: ActionPayload):
    """Hits the Docker SDK to physically modify container boundaries without shutting it down."""
    service = payload.service
    action = payload.recommended_action
    
    if not client:
        logger.error(f"Cannot scale {service}. No Docker connection.")
        return

    try:
        # Match by service label
        containers = client.containers.list(all=True, filters={"name": service})
        if not containers:
            logger.warning(f"Container {service} not found.")
            return
            
        container = containers[0]
        host_config = container.attrs.get('HostConfig', {})
        
        # Base limits defining
        base_mem = 100 * 1024 * 1024 # 100MB
        base_cpu = 5000 # 5% of 100k period
        
        current_mem = host_config.get('Memory', 0)
        current_cpu = host_config.get('CpuQuota', 0)
        
        if current_mem == 0: current_mem = base_mem
        if current_cpu == 0: current_cpu = base_cpu

        update_kwargs = {}
        action_desc = action
        
        scale_start = time.time()
        if action == "upscale_memory":
            new_mem = current_mem + (50 * 1024 * 1024) # +50MB
            update_kwargs['mem_limit'] = new_mem
            update_kwargs['memswap_limit'] = new_mem
            action_desc = f"RAM Expanded to {new_mem // (1024*1024)}MB"
            
        elif action == "upscale_cpu":
            new_cpu = current_cpu + 3000 # +3%
            update_kwargs['cpu_quota'] = new_cpu
            action_desc = f"CPU Quota Expanded to {new_cpu // 1000}%"
            
        elif action == "restart_container":
            container.restart(timeout=0)
            action_desc = "Instant Container Restart (-t 0)"
            
        elif action == "downscale":
            update_kwargs['mem_limit'] = base_mem
            update_kwargs['memswap_limit'] = base_mem
            update_kwargs['cpu_quota'] = base_cpu
            action_desc = "Traffic idle. Releasing resources to cluster."
            
        if update_kwargs:
            container.update(**update_kwargs)
            logger.info(f"[{service}] Docker API Updated: {update_kwargs}")

        scale_duration = (time.time() - scale_start) * 1000
        
        # Push event to dashboard via SSE relay
        event_data = {
            "type": "remediation",
            "service": service,
            "action": action_desc,
            "root_cause": payload.root_cause,
            "confidence": payload.confidence,
            "timing_ms": round(scale_duration, 1),
            "timestamp": datetime.utcnow().isoformat() + "Z"
        }
        
        async with httpx.AsyncClient(timeout=1.0) as http:
            try:
                await http.post(DASHBOARD_URL, json=event_data)
            except Exception:
                pass # Dashboard connection failure shouldn't crash remediation

    except Exception as e:
        logger.error(f"Failed to scale {service}: {e}")

@app.post("/action")
async def trigger_action(req: ActionPayload, bg: BackgroundTasks):
    now = time.time()
    last = COOLDOWN_CACHE.get(req.service, 0)
    
    if (now - last) < COOLDOWN_SECONDS:
        return {"status": "cooldown", "ignored": True}
        
    COOLDOWN_CACHE[req.service] = now
    bg.add_task(execute_dynamic_scale, req)
    
    return {"status": "accepted", "action": req.recommended_action}

@app.get("/health")
def health(): return {"status": "ok"}

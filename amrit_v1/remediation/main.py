from fastapi import FastAPI, HTTPException
from pydantic import BaseModel
import docker
import time
import requests
import os

app = FastAPI()

COOLDOWN_CACHE = {}
COOLDOWN_SECONDS = 120
DASHBOARD_URL = os.environ.get("DASHBOARD_URL", "http://dashboard:3000/api/events")

# Fail fast if docker socket is not available
client = docker.from_env()

class ActionRequest(BaseModel):
    action: str
    target: str
    root_cause: str
    confidence: float

from fastapi import BackgroundTasks

def execute_remediation(target: str, root_cause: str, confidence: float, current_time: float):
    # Execute docker restart (synchronous)
    try:
        containers = client.containers.list(all=True)
        target_container = None
        for c in containers:
            if target in c.name and "db" not in c.name and "user-sim" not in c.name:
                target_container = c
                break
                
        if target_container:
            print(f"Target Acquired: {target_container.name}. Triggering API RESTART...")
            target_container.restart(timeout=5)
            COOLDOWN_CACHE[target] = current_time
        else:
            print(f"Container matching '{target}' not found locally.")
            return

    except Exception as e:
        print(f"API Error during remediation of {target}: {e}")
        return

    # Push event to dashboard
    try:
        requests.post(DASHBOARD_URL, json={
            "service": target,
            "action": "restart_container",
            "timestamp": time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime(current_time)),
            "root_cause": root_cause,
            "confidence": confidence
        }, timeout=0.1)
    except requests.exceptions.RequestException:
        pass # Ignore dashboard timeouts to not fail the remediation request


@app.post("/action")
def handle_action(request: ActionRequest, background_tasks: BackgroundTasks):
    if request.action != "restart":
        raise HTTPException(status_code=400, detail="Unsupported action")

    target = request.target
    current_time = time.time()

    # Cooldown check
    if current_time - COOLDOWN_CACHE.get(target, 0) < COOLDOWN_SECONDS:
        return {"status": "ignored", "reason": "cooldown", "target": target}

    # Offload slow blocking tasks to ensure sub-100ms API response
    background_tasks.add_task(execute_remediation, target, request.root_cause, request.confidence, current_time)

    # Set cooldown early to prevent concurrent requests from getting through
    COOLDOWN_CACHE[target] = current_time

    return {"status": "accepted", "target": target, "action": "restarting"}

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8001)

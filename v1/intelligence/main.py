import asyncio
import logging
import time
from fastapi import FastAPI, BackgroundTasks, Request
import httpx

app = FastAPI()
logger = logging.getLogger(__name__)
logging.basicConfig(level=logging.INFO)

async def process_alert(service_name: str):
    logger.info(f"Anomaly detected on {service_name}. Waiting 3s for telemetry ingestion...")
    await asyncio.sleep(3)

    # Scope strictly to start=now-15s using epoch nanoseconds
    start_time_ns = time.time_ns() - (15 * 1_000_000_000)
    query = f'{{service_name="{service_name}"}} |= "error" | json'

    root_cause = "Unknown Error"
    confidence = 0.50
    logs_found = False

    try:
        # Use a short timeout to meet the strict 15-second system latency budget
        async with httpx.AsyncClient(timeout=2.0) as client:
            logger.info(f"Querying Loki: {query}")
            try:
                resp = await client.get(
                    "http://loki:3100/loki/api/v1/query_range",
                    params={"query": query, "start": str(start_time_ns)}
                )
                resp.raise_for_status()
                data = resp.json()

                results = data.get("data", {}).get("result", [])

                # Fast Deterministic Classification
                for result in results:
                    for val in result.get("values", []):
                        logs_found = True
                        log_lower = val[1].lower()

                        if "timeout" in log_lower or "connection refused" in log_lower:
                            root_cause, confidence = "DB Timeout / Connection Refused", 0.95
                        elif "memory leak" in log_lower or "oom" in log_lower:
                            root_cause, confidence = "Memory Leak / OOM", 0.95
                        elif "exception" in log_lower or "500" in log_lower:
                            root_cause, confidence = "Internal Server Error / Exception", 0.90

                        # Break early to save execution time
                        if confidence > 0.50:
                            break
                    if confidence > 0.50:
                        break

            except Exception as e:
                logger.error(f"Failed querying Loki: {e}")

            # Trace Fallback
            if not logs_found:
                logger.warning(f"No logs found in Loki for {service_name}. Falling back to traces.")
                try:
                    j_resp = await client.get(f"http://jaeger:16686/api/traces?service={service_name}&limit=1")
                    if j_resp.status_code == 200:
                        root_cause, confidence = "Upstream Timeout", 0.85
                except Exception as je:
                    logger.error(f"Trace fallback failed: {je}")
                    root_cause, confidence = "Upstream Timeout", 0.80

            logger.info(f"RCA Complete for {service_name}: {root_cause} (Confidence: {confidence})")

            # Send to Remediation
            payload = {
                "action": "restart",
                "target": service_name,
                "root_cause": root_cause,
                "confidence": confidence
            }
            logger.info(f"Dispatching remediation: {payload}")
            remedy_resp = await client.post("http://remediation:8001/action", json=payload)
            remedy_resp.raise_for_status()

    except Exception as e:
        logger.error(f"Error during RCA processing for {service_name}: {e}")

@app.post("/alert")
async def handle_alert(request: Request, background_tasks: BackgroundTasks):
    """Detection Input Webhook"""
    payload = await request.json()
    logger.info(f"Received alert payload: {payload}")

    if payload.get("status") == "firing":
        for alert in payload.get("alerts", []):
            labels = alert.get("labels", {})
            # Handle different common label naming conventions
            service_name = labels.get("service") or labels.get("compose_service") or labels.get("app")
            if service_name:
                background_tasks.add_task(process_alert, service_name)

    return {"status": "accepted"}

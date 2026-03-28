import asyncio
import json
import os
import time
import httpx

# We reuse the logic from main.py by importing if we want, or just copy it.
# It is simpler to redefine the query logic here as a script.

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

OUTPUT_DIR = "/home/xd/Coding/colony_ps3/v2/intelligence/training/data/"
os.makedirs(OUTPUT_DIR, exist_ok=True)

async def trigger_locust():
    # Placeholder for locust trigger, just sleeps for 1s to simulate normal traffic
    await asyncio.sleep(1)

async def inject_fault(scenario):
    url = f"http://{scenario['service']}:{scenario['port']}{scenario['endpoint']}"
    async with httpx.AsyncClient() as client:
        try:
            print(f"Injecting fault: {url}")
            await client.get(url, timeout=2.0)
        except Exception as e:
            print(f"Fault injected (or failed to connect): {e}")

async def collect_telemetry(service):
    start_time_ns = time.time_ns() - (15 * 1_000_000_000)
    end_time_s = time.time()
    start_time_s = end_time_s - 60

    logs = []
    metrics = []
    traces = []

    async with httpx.AsyncClient() as client:
        # Logs
        try:
            resp = await client.get(
                "http://loki:3100/loki/api/v1/query_range",
                params={"query": f'{{app="{service}"}} | json', "start": str(start_time_ns), "limit": 50}
            )
            if resp.status_code == 200:
                results = resp.json().get("data", {}).get("result", [])
                for res in results:
                    for val in res.get("values", []):
                        try:
                            logs.append(json.loads(val[1]).get("message", val[1]))
                        except:
                            logs.append(val[1])
        except Exception as e:
            print(f"Loki error: {e}")

        # Metrics
        try:
            resp = await client.get(
                "http://prometheus:9090/api/v1/query_range",
                params={"query": f'http_server_duration_milliseconds_sum{{service="{service}"}}', "start": str(start_time_s), "end": str(end_time_s), "step": "1s"}
            )
            if resp.status_code == 200:
                results = resp.json().get("data", {}).get("result", [])
                if results:
                    metrics = results[0].get("values", [])
        except Exception as e:
            print(f"Prometheus error: {e}")

        # Traces
        try:
            resp = await client.get(f"http://jaeger:16686/api/traces?service={service}&limit=10")
            if resp.status_code == 200:
                data = resp.json().get("data", [])
                for trace in data:
                    for span in trace.get("spans", []):
                        process_id = span.get("processID")
                        svc_name = trace.get("processes", {}).get(process_id, {}).get("serviceName", "")
                        if svc_name == service:
                            status_code = 200
                            for tag in span.get("tags", []):
                                if tag.get("key") == "error" and tag.get("value") == True:
                                    status_code = 500
                                if tag.get("key") == "http.status_code":
                                    status_code = tag.get("value")
                            traces.append({
                                "service_name": svc_name,
                                "operation_name": span.get("operationName", ""),
                                "duration_us": span.get("duration", 0),
                                "status_code": status_code
                            })
        except Exception as e:
            print(f"Jaeger error: {e}")

    return logs, metrics, traces

async def main():
    sample_id = 0
    # Fault samples
    for scenario in FAULT_SCENARIOS:
        print(f"Generating data for {scenario['label']} on {scenario['service']}...")
        for i in range(100):
            await trigger_locust()
            await inject_fault(scenario)
            await asyncio.sleep(3) # Wait for telemetry

            logs, metrics, traces = await collect_telemetry(scenario['service'])
            sample = {
                "label": scenario["label"],
                "service": scenario["service"],
                "logs": logs,
                "metrics": metrics,
                "traces": traces
            }

            with open(os.path.join(OUTPUT_DIR, f"sample_{sample_id}.json"), "w") as f:
                json.dump(sample, f)
            sample_id += 1
            print(f"  Sample {i+1}/100 collected.")

    # Normal samples
    print(f"Generating data for normal_operation on frontend-service...")
    for i in range(100):
        await trigger_locust()
        await asyncio.sleep(3) # Wait for telemetry

        logs, metrics, traces = await collect_telemetry("frontend-service")
        sample = {
            "label": "normal_degradation", # Map normal operation to a class we have
            "service": "frontend-service",
            "logs": logs,
            "metrics": metrics,
            "traces": traces
        }

        with open(os.path.join(OUTPUT_DIR, f"sample_{sample_id}.json"), "w") as f:
            json.dump(sample, f)
        sample_id += 1
        print(f"  Sample {i+1}/100 collected.")

if __name__ == "__main__":
    asyncio.run(main())

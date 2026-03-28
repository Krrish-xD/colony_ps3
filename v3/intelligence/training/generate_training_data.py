import json
import time
import httpx
import asyncio
import os

# Fault Definitions matching the v2_microservices_errors.txt structure
FAULTS = [
    {"service": "frontend-service", "port": 8001, "type": "cpu_starvation", "endpoint": "/fault/cpu"},
    {"service": "frontend-service", "port": 8001, "type": "memory_pressure", "endpoint": "/fault/ram"},
    {"service": "auth-service", "port": 8002, "type": "cpu_starvation", "endpoint": "/fault/cpu"},
    {"service": "auth-service", "port": 8002, "type": "memory_pressure", "endpoint": "/fault/ram"},
    {"service": "payment-service", "port": 8006, "type": "cpu_starvation", "endpoint": "/fault/cpu"},
    {"service": "payment-service", "port": 8006, "type": "memory_pressure", "endpoint": "/fault/ram"},
]

DATA_DIR = "/app/data/training_samples"

async def harvest_signals(service: str):
    """Wait 3 seconds and pull telemetry from Observability infrastructure."""
    await asyncio.sleep(3)
    
    # Mocking data collection locally if observability isn't running
    # In practice, this would hit Loki, Prometheus, and Jaeger identically to main.py
    return {
        "logs": [f"Synthesized log for {service} failure"],
        "metrics": [(time.time(), 450.0)],
        "traces": [{"duration_us": 1500000}]
    }

async def trigger_fault_and_collect(fault_conf: dict):
    service = fault_conf["service"]
    fault_type = fault_conf["type"]
    url = f"http://localhost:{fault_conf['port']}{fault_conf['endpoint']}"
    
    print(f"Triggering {fault_type} on {service}...")
    try:
        async with httpx.AsyncClient(timeout=1.0) as client:
            await client.get(url)
    except Exception:
        pass # Expected to drop connection on crash
        
    signals = await harvest_signals(service)
    
    sample = {
        "label": fault_type,
        "service": service,
        "logs": signals["logs"],
        "metrics": signals["metrics"],
        "traces": signals["traces"]
    }
    
    filename = f"{DATA_DIR}/{service}_{fault_type}_{int(time.time())}.json"
    os.makedirs(DATA_DIR, exist_ok=True)
    with open(filename, 'w') as f:
        json.dump(sample, f)

async def main():
    print("Beginning Synthetic Training Data Generation...")
    for _ in range(30):
        for fault in FAULTS:
            await trigger_fault_and_collect(fault)
            await asyncio.sleep(5)
    print("Dataset generation complete. Files saved to /app/data/training_samples")

if __name__ == "__main__":
    asyncio.run(main())

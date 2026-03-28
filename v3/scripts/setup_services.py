import os
import json
from pathlib import Path

BASE_DIR = Path(r"d:\Tech_Solstice_26\colony_ps3\v3\services")

SERVICES = {
    "frontend": {"port": 8001, "downstream": ["auth", "catalog", "cart"]},
    "catalog": {"port": 8003, "downstream": ["inventory"]},
    "cart": {"port": 8004, "downstream": ["catalog"]},
    "inventory": {"port": 8005, "downstream": []},
    "payment": {"port": 8006, "downstream": ["notification"]},
    "shipping": {"port": 8007, "downstream": ["inventory"]},
    "recommendation": {"port": 8008, "downstream": ["catalog"]},
    "notification": {"port": 8009, "downstream": []}
}

REQUIREMENTS = """fastapi==0.109.2
uvicorn==0.27.1
pydantic==2.6.1
prometheus-client==0.19.0
prometheus-fastapi-instrumentator==6.1.0
opentelemetry-api==1.22.0
opentelemetry-sdk==1.22.0
opentelemetry-instrumentation-fastapi==0.43b0
opentelemetry-exporter-otlp==1.22.0
python-json-logger==2.0.7
requests
"""

MAIN_PY_TEMPLATE = """import time
import random
import logging
import requests
from pythonjsonlogger import jsonlogger
from fastapi import FastAPI, HTTPException
from pydantic import BaseModel

from prometheus_fastapi_instrumentator import Instrumentator
from opentelemetry import trace
from opentelemetry.sdk.trace import TracerProvider
from opentelemetry.sdk.trace.export import BatchSpanProcessor
from opentelemetry.exporter.otlp.proto.http.trace_exporter import OTLPSpanExporter
from opentelemetry.sdk.resources import Resource
from opentelemetry.instrumentation.fastapi import FastAPIInstrumentor
from opentelemetry.instrumentation.requests import RequestsInstrumentor

# 1. Tracing Setup (Jaeger via OTLP)
resource = Resource.create({{"service.name": "{service_name}"}})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
trace.get_tracer_provider().add_span_processor(span_processor)

# instrument requests
RequestsInstrumentor().instrument()

# 2. Logging Setup (Loki JSON structured logs)
logger = logging.getLogger("{service_name}-service")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(service)s %(message)s')
logHandler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(logHandler)
logger = logging.LoggerAdapter(logger, extra={{"service": "{service_name}"}})

app = FastAPI(title="{service_name} Service", version="3.0.0")

# 3. HTTP Traces
FastAPIInstrumentor.instrument_app(app)

# 4. Metrics (/metrics)
Instrumentator().instrument(app).expose(app)

def simulate_latency_and_errors():
    with tracer.start_as_current_span("simulate_latency"):
        time.sleep(random.uniform(0.01, 0.05))

@app.get("/")
async def root():
    logger.info("Handling root request for {service_name}")
    simulate_latency_and_errors()
    
    # downstream simulation
    downstreams = {downstream_list}
    responses = []
    
    for ds in downstreams:
        try:
             logger.info(f"Calling downstream {{ds}}")
             with tracer.start_as_current_span(f"call_{{ds}}"):
                 res = requests.get(f"http://{{ds}}:8000/health", timeout=2)
                 responses.append({{ds: res.status_code}})
        except Exception as e:
             logger.error(f"Downstream call failed for {{ds}}", extra={{"error": str(e)}})
             responses.append({{ds: "error"}})
    
    return {{"service": "{service_name}", "downstreams": responses}}

@app.get("/health")
async def health():
    return {{"status": "ok"}}
"""

DOCKERFILE_TEMPLATE = """FROM public.ecr.aws/docker/library/python:3.11-slim
WORKDIR /app
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt
COPY main.py .
EXPOSE 8000
CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "8000"]
"""

COMPOSE_PREFIX = """version: '3.8'

networks:
  colony-net:
    driver: bridge

services:
  otel-collector:
    image: otel/opentelemetry-collector:latest
    networks:
      - colony-net
    ports:
      - "4318:4318" # OTLP HTTP

  auth:
    build: ./services/auth
    ports:
      - "8002:8000"
    networks:
      - colony-net
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
"""

def setup():
    BASE_DIR.mkdir(parents=True, exist_ok=True)
    
    compose_str = COMPOSE_PREFIX
    
    for svc, details in SERVICES.items():
        svc_dir = BASE_DIR / svc
        svc_dir.mkdir(exist_ok=True)
        
        # main.py
        with open(svc_dir / "main.py", "w") as f:
            f.write(MAIN_PY_TEMPLATE.format(
                service_name=svc,
                downstream_list=json.dumps(details["downstream"])
            ))
            
        # requirements.txt
        with open(svc_dir / "requirements.txt", "w") as f:
            f.write(REQUIREMENTS)
            
        # Dockerfile
        with open(svc_dir / "Dockerfile", "w") as f:
            f.write(DOCKERFILE_TEMPLATE)
            
        # Add to docker-compose
        compose_str += f"""
  {svc}:
    build: ./services/{svc}
    ports:
      - "{details['port']}:8000"
    networks:
      - colony-net
    environment:
      - OTEL_EXPORTER_OTLP_ENDPOINT=http://otel-collector:4318
"""

    compose_path = BASE_DIR.parent / "docker-compose.yml"
    with open(compose_path, "w") as f:
        f.write(compose_str)
        
    print("Scaffolding completed.")

if __name__ == "__main__":
    setup()

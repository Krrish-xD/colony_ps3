import time
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
resource = Resource.create({"service.name": "frontend"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://otel-collector:4318/v1/traces"))
trace.get_tracer_provider().add_span_processor(span_processor)

# instrument requests
RequestsInstrumentor().instrument()

# 2. Logging Setup (Loki JSON structured logs)
logger = logging.getLogger("frontend-service")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(service)s %(message)s')
logHandler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(logHandler)
logger = logging.LoggerAdapter(logger, extra={"service": "frontend"})

app = FastAPI(title="frontend Service", version="3.0.0")

# 3. HTTP Traces
FastAPIInstrumentor.instrument_app(app)

# 4. Metrics (/metrics)
Instrumentator().instrument(app).expose(app)

def simulate_latency_and_errors():
    with tracer.start_as_current_span("simulate_latency"):
        time.sleep(random.uniform(0.01, 0.05))

@app.get("/")
async def root():
    logger.info("Handling root request for frontend")
    simulate_latency_and_errors()
    
    # downstream simulation
    downstreams = ["auth", "catalog", "cart"]
    responses = []
    
    for ds in downstreams:
        try:
             logger.info(f"Calling downstream {ds}")
             with tracer.start_as_current_span(f"call_{ds}"):
                 res = requests.get(f"http://{ds}:8000/health", timeout=2)
                 responses.append({ds: res.status_code})
        except Exception as e:
             logger.error(f"Downstream call failed for {ds}", extra={"error": str(e)})
             responses.append({ds: "error"})
    
    return {"service": "frontend", "downstreams": responses}

@app.get("/health")
async def health():
    return {"status": "ok"}

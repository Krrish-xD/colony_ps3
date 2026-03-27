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

# --- Configuration ---
SERVICE_NAME = os.getenv("SERVICE_NAME", "frontend-service")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "http://auth-service:8081")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://localhost:4318")

# --- OpenTelemetry Setup ---
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

# --- FastAPI App ---
app = FastAPI(title=SERVICE_NAME)

FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

# --- Logging ---
def log_event(level, message, error_type=None):
    current_span = trace.get_current_span()
    trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span and current_span.get_span_context().is_valid else ""

    log_data = {
        "service": SERVICE_NAME,
        "level": level,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id
    }
    if error_type:
        log_data["error_type"] = error_type

    print(json.dumps(log_data), flush=True)

# --- Endpoints ---
@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/process")
def process():
    log_event("info", "Processing request")
    if DOWNSTREAM_URL:
        try:
            response = requests.get(f"{DOWNSTREAM_URL}/process", timeout=10)
            response.raise_for_status()
            return {"service": SERVICE_NAME, "downstream": response.json()}
        except Exception as e:
            log_event("error", f"Failed to call downstream service: {str(e)}", error_type=type(e).__name__)
            return JSONResponse(status_code=500, content={"error": "Downstream call failed"})
    else:
        return {"service": SERVICE_NAME, "status": "completed"}

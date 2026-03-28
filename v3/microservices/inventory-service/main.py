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

SERVICE_NAME = os.getenv("SERVICE_NAME", "inventory-service")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")

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

app = FastAPI(title=SERVICE_NAME)
FastAPIInstrumentor.instrument_app(app)
RequestsInstrumentor().instrument()

def log_event(level, message, error_type=""):
    current_span = trace.get_current_span()
    trace_id = format(current_span.get_span_context().trace_id, '032x') if current_span and current_span.get_span_context().is_valid else ""

    log_data = {
        "service": SERVICE_NAME,
        "level": level,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "error_type": error_type
    }
    print(json.dumps(log_data), flush=True)

@app.get("/health")
def health():
    return {"status": "ok"}

@app.get("/process")
def process():
    log_event("info", f"{SERVICE_NAME} received request. Processing and forwarding downstream.")
    if DOWNSTREAM_URL:
        try:
            response = requests.get(f"{DOWNSTREAM_URL}/process", timeout=10)
            response.raise_for_status()
            log_event("info", f"Downstream call to {DOWNSTREAM_URL} succeeded with status {response.status_code}.")
            return {"service": SERVICE_NAME, "downstream": response.json()}
        except requests.exceptions.ConnectionError as e:
            log_event("error", f"Downstream target {DOWNSTREAM_URL} refused connection. Network unreachable.", error_type="ConnectionError")
            return JSONResponse(status_code=502, content={"error": "Downstream connection refused"})
        except requests.exceptions.Timeout as e:
            log_event("error", f"Downstream target {DOWNSTREAM_URL} timed out after 10 seconds. Service unresponsive.", error_type="TimeoutError")
            return JSONResponse(status_code=504, content={"error": "Downstream timeout"})
        except Exception as e:
            log_event("error", f"Downstream call to {DOWNSTREAM_URL} failed unexpectedly: {str(e)}", error_type=type(e).__name__)
            return JSONResponse(status_code=500, content={"error": "Downstream call failed"})
    else:
        log_event("info", f"{SERVICE_NAME} is a leaf node. Processing complete.")
        return {"service": SERVICE_NAME, "status": "completed"}

@app.get("/fault/crash")
def fault_crash():
    log_event("error", f"{SERVICE_NAME} received crash injection. Process terminating immediately.", error_type="CrashInjection")
    os._exit(1)

@app.get("/fault/timeout")
def fault_timeout():
    log_event("warning", f"{SERVICE_NAME} received timeout injection. Sleeping for 7 seconds to simulate unresponsive state.", error_type="TimeoutInjection")
    time.sleep(7)
    log_event("info", f"{SERVICE_NAME} timeout injection complete. Resuming normal operation.")
    return {"status": "timeout_finished"}

@app.get("/fault/error")
def fault_error():
    log_event("error", f"{SERVICE_NAME} received error injection. Returning HTTP 500 Internal Server Error.", error_type="ErrorInjection")
    return JSONResponse(status_code=500, content={"error": "Simulated internal server error"})

@app.get("/fault/cpu")
def fault_cpu():
    log_event("error", "FATAL [inventory] Epoll wait CPU spike: process killed by python watchdog", error_type="LoopSaturationCrash")
    time.sleep(10)
    os._exit(1)

@app.get("/fault/ram")
def fault_ram():
    log_event("error", "ERROR [inventory] Out of memory: killed process (mysql-buffer-pool)", error_type="TransactionBufferOOM")
    leak = []
    for _ in range(5000):
        leak.append("A" * 1024)
    time.sleep(3)
    os._exit(1)

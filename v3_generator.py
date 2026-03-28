import os

SERVICES = [
    {
        "name": "frontend-service",
        "port": 8001,
        "downstream": "http://auth-service:8002",
        "cpu_log": "FATAL [frontend] thread panicked: max CPU time exceeded during template parsing (100% utilization)",
        "ram_log": "FATAL [frontend] V8 JavaScript heap out of memory",
        "cpu_type": "TemplateRenderingCrash",
        "ram_type": "SessionLeakOOM"
    },
    {
        "name": "auth-service",
        "port": 8002,
        "downstream": "http://catalog-service:8003",
        "cpu_log": "FATAL [auth] Bcrypt hash calculation timeout: authentication worker threads deadlocked",
        "ram_log": "FATAL [auth.cache] runtime error: cannot allocate memory for map[string]SessionToken",
        "cpu_type": "CryptographicOverload",
        "ram_type": "TokenCacheOOM"
    },
    {
        "name": "catalog-service",
        "port": 8003,
        "downstream": "http://inventory-service:8005",
        "cpu_log": "ERROR [catalog.search] panic: CPU timeout exceeded matching regex against product descriptions",
        "ram_log": "FATAL [catalog.api] java.lang.OutOfMemoryError: Java heap space fetching products",
        "cpu_type": "RegexBacktrackingCrash",
        "ram_type": "LargeResultSetOOM"
    },
    {
        "name": "cart-service",
        "port": 8004,
        "downstream": "http://catalog-service:8003",
        "cpu_log": "FATAL [cart] Thread deadlocked spinning on sync.Mutex from high CPU contention",
        "ram_log": "FATAL [cart] Python memory allocation failed: unable to allocate 1048576 bytes",
        "cpu_type": "ThreadSpinDeadlock",
        "ram_type": "ArrayExpansionOOM"
    },
    {
        "name": "inventory-service",
        "port": 8005,
        "downstream": "",
        "cpu_log": "FATAL [inventory] Epoll wait CPU spike: process killed by python watchdog",
        "ram_log": "ERROR [inventory] Out of memory: killed process (mysql-buffer-pool)",
        "cpu_type": "LoopSaturationCrash",
        "ram_type": "TransactionBufferOOM"
    },
    {
        "name": "payment-service",
        "port": 8006,
        "downstream": "http://notification-service:8009",
        "cpu_log": "WARN [payment] Thread dumped: Fraud inference model took 100% CPU on Core 0",
        "ram_log": "FATAL [payment.batch] panic: runtime error: out of memory allocating batch chunk",
        "cpu_type": "FraudFilterSpike",
        "ram_type": "BatchProcessingOOM"
    },
    {
        "name": "shipping-service",
        "port": 8007,
        "downstream": "http://inventory-service:8005",
        "cpu_log": "FATAL [shipping.routing] maximum recursion depth exceeded in distance_matrix_calc",
        "ram_log": "FATAL [shipping] heap limits exceeded allocating HTTP response buffer container",
        "cpu_type": "RoutingAlgorithmCrash",
        "ram_type": "PayloadDeserializationLeak"
    },
    {
        "name": "recommendation-service",
        "port": 8008,
        "downstream": "http://catalog-service:8003",
        "cpu_log": "ERROR [recommender.model] Tensor allocation stalled: CPU worker thread blocked for 60s",
        "ram_log": "FATAL [recommender] failed to map physical segment from shared object: Cannot allocate memory",
        "cpu_type": "MatrixMultiplicationOverload",
        "ram_type": "ModelCheckpointOOM"
    },
    {
        "name": "notification-service",
        "port": 8009,
        "downstream": "",
        "cpu_log": "FATAL [notification] Task thread pool exhausted by runaway CPU polling loop",
        "ram_log": "FATAL [notification.queue] java.lang.OutOfMemoryError: failed to append to LinkedBlockingQueue",
        "cpu_type": "SMTPRetryStormCrash",
        "ram_type": "EmailQueueBlockOOM"
    }
]

REQ_TXT = """fastapi==0.110.0
uvicorn==0.28.0
requests==2.31.0
opentelemetry-distro==0.44b0
opentelemetry-exporter-otlp==1.23.0
opentelemetry-instrumentation-fastapi==0.44b0
opentelemetry-instrumentation-requests==0.44b0
"""

DOCKER_TMPL = """FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

EXPOSE {port}

COPY main.py .

CMD ["uvicorn", "main:app", "--host", "0.0.0.0", "--port", "{port}"]
"""

MAIN_TMPL = """import os
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

SERVICE_NAME = os.getenv("SERVICE_NAME", "{name}")
DOWNSTREAM_URL = os.getenv("DOWNSTREAM_URL", "{downstream}")
OTLP_ENDPOINT = os.getenv("OTEL_EXPORTER_OTLP_ENDPOINT", "http://otel-collector:4318")

resource = Resource(attributes={{
    ResourceAttributes.SERVICE_NAME: SERVICE_NAME
}})

# Traces
tracer_provider = TracerProvider(resource=resource)
trace.set_tracer_provider(tracer_provider)
otlp_trace_exporter = OTLPSpanExporter(endpoint=f"{{OTLP_ENDPOINT}}/v1/traces")
span_processor = BatchSpanProcessor(otlp_trace_exporter)
tracer_provider.add_span_processor(span_processor)

# Metrics
otlp_metric_exporter = OTLPMetricExporter(endpoint=f"{{OTLP_ENDPOINT}}/v1/metrics")
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

    log_data = {{
        "service": SERVICE_NAME,
        "level": level,
        "message": message,
        "timestamp": datetime.datetime.utcnow().isoformat() + "Z",
        "trace_id": trace_id,
        "error_type": error_type
    }}
    print(json.dumps(log_data), flush=True)

@app.get("/health")
def health():
    return {{"status": "ok"}}

@app.get("/process")
def process():
    log_event("info", f"{{SERVICE_NAME}} received request. Processing and forwarding downstream.")
    if DOWNSTREAM_URL:
        try:
            response = requests.get(f"{{DOWNSTREAM_URL}}/process", timeout=10)
            response.raise_for_status()
            log_event("info", f"Downstream call to {{DOWNSTREAM_URL}} succeeded with status {{response.status_code}}.")
            return {{"service": SERVICE_NAME, "downstream": response.json()}}
        except requests.exceptions.ConnectionError as e:
            log_event("error", f"Downstream target {{DOWNSTREAM_URL}} refused connection. Network unreachable.", error_type="ConnectionError")
            return JSONResponse(status_code=502, content={{"error": "Downstream connection refused"}})
        except requests.exceptions.Timeout as e:
            log_event("error", f"Downstream target {{DOWNSTREAM_URL}} timed out after 10 seconds. Service unresponsive.", error_type="TimeoutError")
            return JSONResponse(status_code=504, content={{"error": "Downstream timeout"}})
        except Exception as e:
            log_event("error", f"Downstream call to {{DOWNSTREAM_URL}} failed unexpectedly: {{str(e)}}", error_type=type(e).__name__)
            return JSONResponse(status_code=500, content={{"error": "Downstream call failed"}})
    else:
        log_event("info", f"{{SERVICE_NAME}} is a leaf node. Processing complete.")
        return {{"service": SERVICE_NAME, "status": "completed"}}

@app.get("/fault/crash")
def fault_crash():
    log_event("error", f"{{SERVICE_NAME}} received crash injection. Process terminating immediately.", error_type="CrashInjection")
    os._exit(1)

@app.get("/fault/timeout")
def fault_timeout():
    log_event("warning", f"{{SERVICE_NAME}} received timeout injection. Sleeping for 7 seconds to simulate unresponsive state.", error_type="TimeoutInjection")
    time.sleep(7)
    log_event("info", f"{{SERVICE_NAME}} timeout injection complete. Resuming normal operation.")
    return {{"status": "timeout_finished"}}

@app.get("/fault/error")
def fault_error():
    log_event("error", f"{{SERVICE_NAME}} received error injection. Returning HTTP 500 Internal Server Error.", error_type="ErrorInjection")
    return JSONResponse(status_code=500, content={{"error": "Simulated internal server error"}})

@app.get("/fault/cpu")
def fault_cpu():
    log_event("error", "{cpu_log}", error_type="{cpu_type}")
    time.sleep(10)
    os._exit(1)

@app.get("/fault/ram")
def fault_ram():
    log_event("error", "{ram_log}", error_type="{ram_type}")
    leak = []
    for _ in range(5000):
        leak.append("A" * 1024)
    time.sleep(3)
    os._exit(1)
"""

base_dir = "/Users/rishirajsinhvihol/Documents/techsolistice/colony_ps3/v3/microservices"
os.makedirs(base_dir, exist_ok=True)

for s in SERVICES:
    svc_dir = os.path.join(base_dir, s['name'])
    os.makedirs(svc_dir, exist_ok=True)
    
    with open(os.path.join(svc_dir, "requirements.txt"), "w") as f:
        f.write(REQ_TXT)
        
    with open(os.path.join(svc_dir, "Dockerfile"), "w") as f:
        f.write(DOCKER_TMPL.format(port=s['port']))
        
    with open(os.path.join(svc_dir, "main.py"), "w") as f:
        f.write(MAIN_TMPL.format(
            name=s['name'],
            downstream=s['downstream'],
            cpu_log=s['cpu_log'],
            ram_log=s['ram_log'],
            cpu_type=s['cpu_type'],
            ram_type=s['ram_type']
        ))

print("v3 microservices and custom endpoints generated successfully in " + base_dir)

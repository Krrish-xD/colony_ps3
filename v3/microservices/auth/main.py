import time
import random
import logging
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

# 1. Tracing Setup (Jaeger via OTLP)
resource = Resource.create({"service.name": "auth"})
trace.set_tracer_provider(TracerProvider(resource=resource))
tracer = trace.get_tracer(__name__)
span_processor = BatchSpanProcessor(OTLPSpanExporter(endpoint="http://localhost:4318/v1/traces"))
trace.get_tracer_provider().add_span_processor(span_processor)

# 2. Logging Setup (Loki JSON structured logs)
logger = logging.getLogger("auth-service")
logger.setLevel(logging.INFO)
logHandler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter('%(asctime)s %(levelname)s %(name)s %(service)s %(message)s')
logHandler.setFormatter(formatter)
logger.handlers.clear()
logger.addHandler(logHandler)
# Helper to always enforce service label
logger = logging.LoggerAdapter(logger, extra={"service": "auth"})

app = FastAPI(title="Auth Service", version="3.0.0")

# 3. Automagically instrument FastAPI for traces
FastAPIInstrumentor.instrument_app(app)

# 4. Automagically instrument FastAPI for metrics (/metrics)
Instrumentator().instrument(app).expose(app)

class LoginRequest(BaseModel):
    username: str
    password: str

class ValidateRequest(BaseModel):
    token: str

def simulate_latency_and_errors():
    with tracer.start_as_current_span("simulate_latency"):
        time.sleep(random.uniform(0.01, 0.05))

@app.post("/login")
async def login(req: LoginRequest):
    logger.info("Login attempt", extra={"username": req.username})
    simulate_latency_and_errors()
    
    if req.username == "admin" and req.password == "admin":
        logger.info("Login successful")
        return {"token": "valid-token-123", "user": req.username}
    
    logger.warning("Login failed", extra={"reason": "Invalid credentials"})
    raise HTTPException(status_code=401, detail="Invalid credentials")

@app.post("/validate")
async def validate(req: ValidateRequest):
    logger.info("Token validation attempt")
    simulate_latency_and_errors()
    
    if req.token == "valid-token-123":
        logger.info("Token validation successful")
        return {"valid": True, "user": "admin"}
    
    logger.warning("Token validation failed")
    raise HTTPException(status_code=401, detail="Invalid token")

@app.get("/health")
async def health():
    return {"status": "ok"}

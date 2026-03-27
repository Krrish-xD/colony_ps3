# 🎯 Global Jules Context

## The Problem Statement
You are participating in a 30-hour Hackathon. The objective is to build a real-time AI observability system that ingests live logs and metrics from a distributed application, performs root cause analysis, and triggers automated remediation end-to-end under 15 seconds. 

## The Target System Architecture
We are building a 4-tier microservice architecture (Frontend, Auth, Cart, Payment) instrumented with OpenTelemetry.
- Locust generates background traffic and triggers deliberate chaos.
- Telemetry flows to an OTel Collector, which routes to Prometheus, Loki, and Jaeger.
- Prometheus Alertmanager evaluates PromQL rules (e.g., `rate(http_5xx) > 5%`).
- When tripped, a push webhook hits our Python RCA Engine. The engine waits 3 seconds (micro-buffer for ingestion latency), safely queries Loki for logs on the exact failing service, maps the error to a known issue, and sends an action back to our Auto-Remediation Engine.
- The Remediation Engine restarts the container via the Docker socket (checking a 30s cooldown cache to prevent infinite loops).
- A Next.js Server-Sent Events (SSE) Dashboard pulses the system nodes in real time to visualize the failure and recovery.

## ⚠️ Global Jules Instructions
1. **Demo Constraint:** Write ONLY what is needed for a 3-minute demo. Omit production auth, TLS, or persistent DB volumes. Optimize everything for sub-100ms execution times to meet the strict 15-second system latency budget.
2. **Determinism:** Do not use probabilistic ML models. Use strict IF/ELSE rule-matching against explicit JSON payload contracts.
3. **Boundary Constraint:** Work EXCLUSIVELY in your assigned directory. Do not drift into modifying other folders. The rest of the team (other Jules instances) is handling the other components.
4. **Environment Constraints:** No Kubernetes. Everything runs on Docker Compose.
5. **Required Reading (CRITICAL):** Before writing any code, you MUST use your tools to read the master architecture document located at `ag_research/final_system_guide.md` in its entirety to understand the system nuances and technical trade-offs.

---

# 🚀 Your Specific Assignment: Instance 1 (Microservices)

**You only work in the `/services` folder.**

Other Jules instances are building the observability pipeline, dashboard, and RCA engine. You do not need to worry about them.

Your task is to build **4 minimal stateless services** into the `/services` directory. 
**CRITICAL INSTRUCTION**: You are NOT required to preserve the original `sock-shop` structure. Do not copy varying complex logic. You must rebuild these minimal services from scratch to ensure a perfectly clean deterministic trace topology.

## 🏗️ Execution Specifications:

1. **Service Naming & Output Tree:**
You must output exactly this directory structure:
```text
/services/
  /frontend-service/
    Dockerfile
    app.js (or main.py)
  /auth-service/
    ...
  /cart-service/
    ...
  /payment-service/
    ...
```

2. **Inter-Service Contract:**
Define explicit sequential service-to-service calls: `Frontend → Auth → Cart → Payment`.
- Each service must expose a `/health` endpoint returning `200 OK`.
- Each service must expose a `/process` endpoint that calls the next service downstream. Normal endpoints must respond in <50ms. Do NOT introduce unnecessary latency. Use simple HTTP clients.

3. **OTel & Trace Context Propagation:**
You must embed the OpenTelemetry SDK (using the OTLP HTTP exporter to `http://localhost:4318`).
- Export traces, metrics, and logs.
- **CRITICAL**: Ensure trace context (`traceparent` HTTP headers) propagates perfectly across the service hops so each request maintains the exact same `trace_id`.

4. **Structured Logging Schema:**
All logs MUST be structured JSON emitted to stdout. They must adhere strictly to this schema:
```json
{
  "service": "<service-name>",
  "level": "info|error",
  "message": "...",
  "timestamp": "...",
  "trace_id": "...",
  "error_type": "optional"
}
```

5. **Chaos Endpoints Behavior:**
You must implement `/fault/crash`, `/fault/timeout`, and `/fault/error` on `payment-service` and `cart-service`.
- `/fault/crash`: Terminate the process `sys.exit(1)` OR raise a catastrophic unhandled exception.
- `/fault/timeout`: Delay the HTTP response by 5–10 seconds.
- `/fault/error`: Return HTTP 500 AND emit the structured error log.

6. **Dockerization Requirement:**
Each service MUST include a `Dockerfile` using a lightweight base image (`node:alpine` or `python:slim`), installing dependencies, and exposing the appropriate port (e.g., 8080). Critically, ensure `package.json` or `requirements.txt` is completely defined so the images build flawlessly out of the box.

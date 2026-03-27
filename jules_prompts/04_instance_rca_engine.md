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

# 🚀 Your Specific Assignment: Instance 4 (RCA Engine)

**You only work in the `/intelligence` folder.**

You are the brain of the system.
Your task is to write a highly optimized Python FastAPI application representing the **RCA Correlation Engine**.

## 🏗️ Execution Specifications:
1. **Detection Input Webhook**: Expose `POST /alert`. Expect the standard Alertmanager payload format where the failing service is deeply nested (e.g., `{"status": "firing", "alerts": [{"labels": {"service": "payment-service"}}...]}`).
2. **Ingestion Micro-Buffer (CRITICAL)**: Immediately run an asynchronous `await asyncio.sleep(3)` upon detection. This is NOT a suggestion. You must wait 3 seconds to guarantee Loki has finished indexing the logs from the `payment-service` crash before querying it.
3. **Targeted LogQL**: Make an explicit HTTP API call to Loki: `http://loki:3100/loki/api/v1/query_range?query={service_name="payment-service"} |= "error" | json` scoped strictly to `start=now-15s`. Note: Loki labels depend on OTel translation, so adjust `service_name` or `compose_service` as needed, but always use the JSON parser to read the structured log output.
4. **Deterministic Classification**: Parse the returned JSON log strings. Use strict string `if/else` checks (e.g., `if "timeout" in error.lower()`) to define the `root_cause`.
5. **Remediation Output Contract**: Build this exact structured JSON payload to fire to the Remediation service (`http://remediation:8001/action`): 
   `{"action": "restart", "target": "<service-name>", "root_cause": "<cause-string>", "confidence": 0.95}`
6. **Dockerization Requirement**: Include a `Dockerfile` utilizing a fast and lightweight Python image (e.g. `python:3.11-slim`). Export port 8000.

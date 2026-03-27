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

# 🚀 Your Specific Assignment: Instance 2 (OTel & Prometheus)

**You only work in the `/observability` folder.**

Other instances are building the microservices and RCA engine.

Your task is to set up the **OpenTelemetry Collector** configuration (`otel-collector-config.yaml`) and the **Prometheus** configuration (`prometheus.yml` + `rules.yml`).
1. Ensure the OTel collector receives trace/metric/log vectors on `0.0.0.0:4318` and routes them properly to Prometheus, Loki, and Jaeger endpoints inside the Docker network.
2. **Prometheus Alert Rules Constraint**: Write explicit, deterministic PromQL alert rules in `rules.yml` specifically looking at service-level anomalies (e.g., `rate(http_requests_total{status=~"5.."}[1m]) > 0.05` and `histogram_quantile(0.95, ...) > 2.0s`).
3. **Webhook Contract Constraint**: Configure Prometheus Alertmanager (`alertmanager.yml`) to POST an HTTP JSON Webhook to the RCA engine (`http://intelligence:8000/alert`). It is CRITICAL that the webhook passes the `service` label mapped from the application metrics perfectly so the RCA engine knows the exact target node.


--------------------------------------------------
🔁 MANDATORY 2-PASS SELF-REVIEW LOOP
--------------------------------------------------

After completing the initial implementation, you MUST perform 2 full review passes before finalizing.

----------------------------------
PASS 1 — CODE REVIEW (CRITICAL)
----------------------------------

Analyze your own code for:

- correctness (will it actually run?)
- missing requirements from prompt
- broken inter-service communication
- incorrect OpenTelemetry setup
- missing or malformed logs
- incorrect chaos endpoint behavior

Output:

## Pass 1 Review
- Issues Found
- Why they are problems
- Fixes to apply

Then APPLY all fixes.

----------------------------------
PASS 2 — OPTIMIZATION & SIMPLIFICATION
----------------------------------

Now optimize for:

- performance (latency, unnecessary overhead)
- simplicity (remove unnecessary code)
- clarity (clean structure)
- Docker image size
- startup speed

Output:

## Pass 2 Optimization
- Improvements made
- What was removed or simplified
- Final justification of design

----------------------------------
FINAL OUTPUT
----------------------------------

Only after BOTH passes:

- output final cleaned code
- ensure all requirements are satisfied
- ensure system is minimal and fast

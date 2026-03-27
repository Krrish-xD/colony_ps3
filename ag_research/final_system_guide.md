# Master System Documentation: The 15-Second Automated Deterministic Response System (Revised)

## 1. Introduction
Modern scalable infrastructure is highly distributed. A single user click can span dozens of decoupled microservices, moving across complex network meshes and ephemeral containers. When something breaks—a sudden latency spike or an arbitrary service crash—finding the needle in the haystack is a grueling manual process. On-call engineers scramble to cross-reference multiple dashboards, write complex log queries, and manually restart failing components.

Our system solves this problem fundamentally. We have designed a closed-loop observability automation system that watches a running application, instantly detects when something is wrong, figures out exactly where the failure originated, and automatically applies a fix—all within a strict 15-second latency window. 

This guide outlines a highly practical, hackathon-ready architecture that marries deterministic telemetry triggers with rapid, container-level automated remediation.

---

## 2. High-Level System Overview
The pipeline functions as a continuous, high-speed data river running from application footprint to deterministic intelligence, and finally to infrastructural command.

At a high level, the flow is:
1. **Traffic & Chaos Generation**: Simulated traffic (via Locust) hits the microservice architecture, occasionally triggering deliberate "chaos endpoints" to simulate failures.
2. **Unified Telemetry**: Services emit Traces, Metrics, and Logs to a centralized OpenTelemetry (OTel) Collector, which routes them to their respective storage backends (Prometheus, Loki, Jaeger).
3. **Detection**: Prometheus Alertmanager continuously evaluates PromQL rules. When an anomaly threshold is breached, it instantly pushes a Webhook.
4. **Correlation & RCA**: The RCA engine waits a strict 3 seconds to ensure log ingestion completes, then performs a targeted LogQL query on the specific failing service to find the exact error.
5. **Remediation & Audit**: The RCA engine verifies the service isn't in a "cooldown" period, restarts the container via the Docker socket, and streams the event via Server-Sent Events (SSE) to a custom React/Next.js dynamic dependency dashboard.

---

## 3. Explicit System Contracts
To ensure strict component isolation and robust integration, the system data-handoffs rely on rigid JSON contracts instead of arbitrary string parsing:

**Detection Output (Agent C -> Agent D):**
```json
{
  "service": "payment-service",
  "metric": "http_request_duration_seconds",
  "severity": "critical",
  "timestamp": "2023-10-27T10:00:00Z"
}
```

**RCA Output (Agent D Internal Decision):**
```json
{
  "service": "payment-service",
  "root_cause": "DB Timeout / Connection Refused",
  "confidence": 0.95
}
```

**Remediation Input (Agent D -> Docker API / Dashboard Agent E):**
```json
{
  "service": "payment-service",
  "action": "restart_container",
  "timestamp": "2023-10-27T10:00:04Z"
}
```

---

## 4. Core Components Breakdown

### 4.1 Microservices & Traffic Layer
- **What it is**: The system under test (SUT) comprising 4 independent web services (Frontend, Orders, Inventory, Payment) running via Docker Compose. 
- **Traffic**: **Locust** is used to continuously generate HTTP background traffic. It is specifically configured to occasionally hit "chaos endpoints" (e.g., `/fault/timeout`) to easily demonstrate the system's reactivity to the judges.
- **Why Docker Compose**: We chose Docker Compose over Kubernetes. K8s introduces heavy control-plane latency and steep learning curves. Docker Compose ensures millisecond-fast local networking and exposes the host’s Docker socket directly, which is crucial for our high-speed remediation requirements.

### 4.2 Observability Stack (Powered by OTel)
- **OpenTelemetry (OTel) Collector**: The central nervous system of the telemetry pipeline. Applications are instrumented with OpenTelemetry and send all signals to the OTel Collector, which acts as a router.
- **Prometheus (Metrics)**: A time-series database storing request rates, errors, and durations.
- **Loki (Logs)**: A highly efficient log aggregation engine storing structured application logs.
- **Jaeger (Traces)**: A distributed tracing engine tracking the exact path and latency of requests as they hop across the microservice mesh.

### 4.3 Detection Layer (Agent C)
- **What it is**: The trigger mechanism identifying non-standard behavior.
- **Chosen Approach**: **Prometheus Alertmanager + Push Webhooks**. We evaluate static PromQL alert rules every 15s. When tripped, Alertmanager pushes a webhook to the RCA Agent.
- **Concrete Alert Rules**:
  - *High Error Rate*: `rate(http_requests_total{status=~"5.."}[1m]) > 0.05` (Triggers if 5xx errors exceed 5% of traffic. Threshold chosen to ignore stray single errors but catch systemic failures fast).
  - *Latency Spike*: `histogram_quantile(0.95, rate(http_request_duration_seconds_bucket[1m])) > 2.0` (Triggers if the 95th percentile response time exceeds 2 seconds. Chosen because human perception of "broken" UI typically starts around 2s).
- **Why PromQL over pure ML**: Relying purely on an ML model without historical context or fallback is extremely risky for a 3-minute hackathon demo. PromQL alerts are 100% deterministic, guaranteeing the anomaly will trigger successfully during a live presentation. (An Isolation Forest model can optionally run as a secondary, non-blocking warning signal).

### 4.4 Root Cause Analysis (RCA) Engine (Agent D)
- **Targeted Correlation**: When Alertmanager fires, it sends the exact abstract node (e.g., `payment-service`) that triggered the alert. The RCA engine does not scan the whole cluster; it does an O(1) targeted LogQL search (`{app="payment-service"}`) to quickly classify the error ("Connection Refused" vs "DB Timeout").
- **The 3-Second Micro-Buffer**: Querying Loki and Jaeger immediately `[T0-5s, T0]` right after an anomaly is detected will miss critical logs due to a natural 1-2s ingestion/indexing latency. The RCA Engine specifically waits **3 seconds** before querying the last 15 seconds. This micro-buffering subverts the fatal race condition of telemetry ingestion.
- **Trace-Based RCA Fallback**: If Loki returns zero logs (e.g. the service is completely hung and cannot write to stdout), the RCA engine falls back to traces. It queries Jaeger for the `Frontend` trace and traverses the causal graph to find the exact span that dropped the connection, marking the root cause as "Upstream Timeout" instead of "Internal Exception".

### 4.5 Auto-Remediation
- **Execution**: A custom Python microservice mounted with `/var/run/docker.sock` receives the root cause classification, matches it to an action, and executes native Docker commands (e.g., `docker restart payment-service`).
- **Cooldown Cache**: To prevent infinite restart loops while a service is booting back up, the RCA agent maintains an in-memory dictionary tracking `{ "service_name": last_restarted_timestamp }`. Services are completely immune to further remediation for 30 seconds.

### 4.6 Custom Next.js Dashboard (Agent E)
- **What it is**: A custom Next.js / ReactJS application styled with Tailwind CSS, replacing standard Grafana.
- **Dynamic Topology**: Upon startup, the Dashboard makes an HTTP GET call to Jaeger's `/api/dependencies` endpoint to dynamically discover and render the microservice force-directed node graph.
- **Server-Sent Events (SSE)**: The Dashboard streams real-time updates from the RCA engine via SSE. It pulses nodes red during anomalies and green during recovery, printing actions to an Event Log. SSE is natively built into HTTP and is significantly more robust for the browser than raw websockets.

---

## 5. DESIGN DECISIONS

### Why OTel Collector over Direct Ingestion
**Rationale**: Pushing to a unified collector drastically simplifies application-side instrumentation. It centralizes routing logic, standardizes the telemetry format (OTLP), and makes the system wildly more robust and representative of modern enterprise architectures.

### Why Dashboard React + SSE over Grafana
**Rationale**: While Grafana is powerful, a custom React dashboard gives absolute control over the demo narrative. Dynamically drawing a force-directed graph from Jaeger's API and pulsing nodes red/green via SSE creates an incredibly visceral, "wow-factor" presentation for hackathon judges that native Grafana dashboards struggle to match.
**Tradeoffs & Fallbacks**: Building a custom UI costs 4-6 hours of hackathon time. If the React frontend fails or hits infinite re-rendering loops during the demo, our explicit fallback plan is a pre-configured Grafana instance loaded via code-as-configuration standing by on port 3000.

### Why the 3-Second Wait Buffer
**Rationale**: Telemetry isn't perfectly synchronous. A metric might hit Prometheus and trigger an alert in 1 second, but the corresponding log might take 2.5 seconds to be indexed by Loki. Rushing the query results in an empty response and a failed RCA. The 3s buffer trades a tiny bit of latency for 100% correlation accuracy.

---

## 6. SYSTEM FLOW (DETAILED) & HACKATHON SCENARIO

The step-by-step lifecycle of a 9-second recovery:
1. **T=0s**: A judge clicks "Trigger Memory Leak" on the React Dashboard. Locust hits the `/fault/timeout` chaos endpoint on `payment-service`.
2. **T=2s**: HTTP 500 errors spike. The OTel Collector immediately routes this telemetry to Prometheus.
3. **T=4s**: Prometheus Alertmanager rule `rate(http_500[1m]) > 0` fires, pushing a webhook to the RCA Service indicating `payment-service` is highly unhealthy.
4. **T=7s**: The RCA Service wakes up from its 3-second ingestion wait buffer. It queries Loki for `payment-service` logs in the window `[T=0, T=7]`.
5. **T=8s**: Loki returns the log: "Connection Refused: DB timeout". The RCA engine accurately identifies the precise root cause.
6. **T=8.5s**: The RCA Service checks its cooldown cache (service is eligible). It executes `docker restart payment-service` against the Docker socket and POSTs the root cause payload to the React Dashboard backend.
7. **T=9s**: The React Dashboard receives the SSE stream. It pulses the `payment-service` node red, outputs the Event Log "Restarting payment-service...", and pulses the node green again upon recovery. 

**Total Time: 9 seconds.**

---

## 7. REALISTIC LATENCY BUDGET (<15s)

Hitting a 15-second total-time-to-recover ceiling is challenging in the real world. Here is the strict latency budget we adhere to:

| Phase | Time Allotted | Mechanism |
| :--- | :--- | :--- |
| **Detection** | 4s | Prometheus scrape interval (pushing every 2s) + Alertmanager evaluation |
| **Ingestion Buffer** | 3s | Deliberate wait to resolve Loki/Jaeger race condition |
| **RCA Processing** | 1s | Fast O(1) targeted queries against LogQL and Jaeger APIs |
| **Action Execution** | 2s to 4s | Docker Daemon socket command execution to recycle the container |
| **Total** | **~10s to 12s** | Comfortably under the 15s hackathon SLA limit |

---

## 8. SYSTEM FAILURE MODES (RESILIENCE)

A highly autonomous system must gracefully handle failures of its own components.
- **If Loki Query Fails / Misses Logs**: The RCA engine falls back to distributed traces (Jaeger) to deduce the span that hung. If tracing also fails, it falls back to the last known error type, marking the RCA Output with `{"confidence": "low"}`. 
- **If RCA Engine Crashes**: Prometheus Alertmanager is configured with a secondary webhook receiver pointing to a dead-man's switch (e.g., Slack or PagerDuty) so human operators are immediately notified of unhandled alerts.
- **If React Dashboard Fails**: The system is entirely decoupled. The RCA engine and Auto-remediation will continue to function flawlessly in the background. A standby Grafana instance is used for visualization.

---

## 9. KEY INSIGHTS

- **Deterministic Demos win Hackathons**: Tying the primary detection to a deterministic PromQL rule guarantees the system reacts exactly when you press the chaos button. 
- **The Ingestion Race Condition**: The hardest technical curveball in this project is the telemetry race condition. The introduction of the 3-second micro-buffer is the linchpin that makes the entire correlation engine function reliably.

---

## 10. REJECTED IDEAS

Throughout the iterative design rounds, several approaches were explored and discarded:
1. **Python Polling for PromQL**: We initially designed a Python script to poll Prometheus every 5 seconds. Rejected. Polling puts high load on the database. We pivoted entirely to Push Webhooks via Alertmanager.
2. **Immediate RCA querying (Race Conditions)**: Agent D originally queried Loki for the exact `[T0-5s, T0]` window the millisecond it got an anomaly alert. Rejected. Due to ingestion latency, this caused the system to conclude there were no errors.
3. **Hardcoded Dashboard Topology**: We initially assumed the dashboard magically knew the 4 microservices. Rejected. We implemented a dynamic topological discovery step via Jaeger's dependency API to formally prove integration.
4. **Redundant RCA Scanning**: We originally had the RCA engine ignore the Alertmanager's hint and scan *all* traces to find the failure. Rejected. Alertmanager already knows which node failed; passing the `service` identity forward to RCA reduces query times from seconds to milliseconds.

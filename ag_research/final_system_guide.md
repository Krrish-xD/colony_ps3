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
3. **Detection**: Prometheus Alertmanager continuously evaluates PromQL rules. When an anomaly threshold is breached, it instantly pushes aWebhook.
4. **Correlation & RCA**: The RCA engine waits a strict 3 seconds to ensure log ingestion completes, then performs a targeted LogQL query on the specific failing service to find the exact error.
5. **Remediation & Audit**: The RCA engine verifies the service isn't in a "cooldown" period, restarts the container via the Docker socket, and streams the event via Server-Sent Events (SSE) to a custom React/Next.js dynamic dependency dashboard.

---

## 3. Core Components Breakdown

### 3.1 Microservices & Traffic Layer
- **What it is**: The system under test (SUT) comprising 4 independent web services (Frontend, Orders, Inventory, Payment) running via Docker Compose. 
- **Traffic**: **Locust** is used to continuously generate HTTP background traffic. It is specifically configured to occasionally hit "chaos endpoints" (e.g., `/fault/timeout`) to easily demonstrate the system's reactivity to the judges.
- **Why Docker Compose**: We chose Docker Compose over Kubernetes. K8s introduces heavy control-plane latency and steep learning curves. Docker Compose ensures millisecond-fast local networking and exposes the host’s Docker socket directly, which is crucial for our high-speed remediation requirements.

### 3.2 Observability Stack (Powered by OTel)
- **OpenTelemetry (OTel) Collector**: The central nervous system of the telemetry pipeline. Applications are instrumented with OpenTelemetry and send all signals to the OTel Collector, which acts as a router.
- **Prometheus (Metrics)**: A time-series database storing request rates, errors, and durations.
- **Loki (Logs)**: A highly efficient log aggregation engine storing structured application logs.
- **Jaeger (Traces)**: A distributed tracing engine tracking the exact path and latency of requests as they hop across the microservice mesh.

### 3.3 Detection Layer (Agent C)
- **What it is**: The trigger mechanism identifying non-standard behavior.
- **Chosen Approach**: **Prometheus Alertmanager + Push Webhooks**. We evaluate static PromQL alert rules every 15s (e.g., `rate(http_requests_total{status=~"5.."}[1m]) > 0.05`). When tripped, Alertmanager pushes a webhook to the RCA Agent.
- **Optional ML Warning**: While an Isolation Forest model (Python) can run as a secondary signal analyzing 1m latency vectors, the primary trigger is the deterministic PromQL rule.
- **Why PromQL over pure ML**: Relying purely on an ML model without historical context or fallback is extremely risky for a 3-minute hackathon demo. PromQL alerts are 100% deterministic, guaranteeing the anomaly will trigger successfully during a live presentation.

### 3.4 Root Cause Analysis (RCA) Engine (Agent D)
- **Targeted Correlation**: When Alertmanager fires, it sends the exact abstract node (e.g., `payment-service`) that triggered the alert. The RCA engine does not scan the whole cluster; it does an O(1) targeted LogQL search (`{app="payment-service"}`) to quickly classify the error ("Connection Refused" vs "DB Timeout").
- **The 3-Second Micro-Buffer**: Querying Loki and Jaeger immediately `[T0-5s, T0]` right after an anomaly is detected will miss critical logs due to a natural 1-2s ingestion/indexing latency. The RCA Engine specifically waits **3 seconds** before querying the last 15 seconds. This micro-buffering subverts the fatal race condition of telemetry ingestion.

### 3.5 Auto-Remediation
- **Execution**: A custom Python microservice mounted with `/var/run/docker.sock` receives the root cause classification, matches it to an action, and executes native Docker commands (e.g., `docker restart payment-service`).
- **Cooldown Cache**: To prevent infinite restart loops while a service is booting back up, the RCA agent maintains an in-memory dictionary tracking `{ "service_name": last_restarted_timestamp }`. Services are completely immune to further remediation for 30 seconds.

### 3.6 Custom Next.js Dashboard (Agent E)
- **What it is**: A custom Next.js / ReactJS application styled with Tailwind CSS, replacing standard Grafana.
- **Dynamic Topology**: Upon startup, the Dashboard makes an HTTP GET call to Jaeger's `/api/dependencies` endpoint to dynamically discover and render the microservice force-directed node graph.
- **Server-Sent Events (SSE)**: The Dashboard streams real-time updates from the RCA engine via SSE. It pulses nodes red during anomalies and green during recovery, printing actions to an Event Log. SSE is natively built into HTTP and is significantly more robust for the browser than raw websockets.

---

## 4. DESIGN DECISIONS

### Why OTel Collector over Direct Ingestion
**Consideration**: Applications pushing directly to Prometheus, Promtail, and Jaeger.
**Decision**: OpenTelemetry (OTel) Collector.
**Rationale**: Pushing to a unified collector drastically simplifies application-side instrumentation. It centralizes routing logic, standardizes the telemetry format (OTLP), and makes the system wildly more robust and representative of modern enterprise architectures.

### Why Dashboard React + SSE over Grafana
**Consideration**: Unified Grafana RCA Workbench with Annotations.
**Decision**: Custom Next.js React Dashboard with Server-Sent Events.
**Rationale**: While Grafana is powerful, a custom React dashboard gives absolute control over the demo narrative. Dynamically drawing a force-directed graph from Jaeger's API and pulsing nodes red/green via SSE creates an incredibly visceral, "wow-factor" presentation for hackathon judges that native Grafana dashboards struggle to match.

### Why the 3-Second Wait Buffer
**Consideration**: Query Loki the millisecond the webhook fires.
**Decision**: Wait 3 seconds.
**Rationale**: Telemetry isn't perfectly synchronous. A metric might hit Prometheus and trigger an alert in 1 second, but the corresponding log might take 2.5 seconds to be indexed by Loki. Rushing the query results in an empty response and a failed RCA. The 3s buffer trades a tiny bit of latency for 100% correlation accuracy.

---

## 5. SYSTEM FLOW (DETAILED) & HACKATHON SCENARIO

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

## 6. LATENCY STRATEGY (<15s)

Hitting a 15-second total-time-to-recover ceiling requires shaving milliseconds at every boundary constraint:
- **Push Webhooks**: Relying on PromQL Alertmanager Webhooks entirely eliminates polling overhead between the detection and RCA layers.
- **Targeted RCA**: Because Agent C explicitly identifies the abstract node, Agent D doesn't waste seconds scanning the whole cluster; it executes an O(1) query against Loki.
- **SSE Dashboarding**: Server-Sent Events push UI updates instantly and unidirectionally, bypassing heavy client-side polling or websocket handshake delays.

---

## 7. FAILURE SCENARIOS

### Scenario A: Service Crash
- **Event**: A bad payload causes the Orders Service to exit with `code 1`. 
- **Detection**: Error rate metric hits 100%. Alertmanager fires push webhook.
- **RCA**: Logs instantly reveal `panic: nil pointer dereference`. RCA checks cooldown cache.
- **Remediation**: Executes `docker restart orders-service`. Dashboard blinks node red then green.

### Scenario B: Database Latency Spike
- **Event**: A runaway query locks the Postgres database.
- **Detection**: Locust requests hitting the frontend start experiencing massive latency.
- **RCA**: Traces from Jaeger explicitly show the delay is 100% nested in the DB span.
- **Remediation**: The cooldown policy prevents the system from violently restarting a stateful database. It pulses the UI node yellow, logs a "Tier 1 Alert" payload, and awaits manual intervention, demonstrating safe operational boundaries to the judges.

---

## 8. KEY INSIGHTS

- **Deterministic Demos win Hackathons**: Relying purely on ML (Isolation Forest) without historical data during a 3-minute demo is a gamble. Tying the primary detection to a deterministic PromQL rule guarantees the system reacts exactly when you press the chaos button. 
- **The Ingestion Race Condition**: The hardest technical curveball in this project is the telemetry race condition. Because Alertmanager is exceptionally fast, it often alerts the RCA engine *before* the logs have been fully written to Loki's disk. The introduction of the 3-second micro-buffer is the linchpin that makes the entire correlation engine function reliably.

---

## 9. REJECTED IDEAS

Throughout the iterative design rounds, several approaches were explored and discarded:
1. **Python Polling for PromQL**: We initially designed a Python script to poll Prometheus every 5 seconds. Rejected. Polling puts high load on the database and clashes with 1s scraping intervals. We pivoted entirely to Push Webhooks via Alertmanager.
2. **Immediate RCA querying (Race Conditions)**: Agent D originally queried Loki for the exact `[T0-5s, T0]` window the millisecond it got an anomaly alert. Rejected. Due to ingestion latency, this caused the system to conclude there were no errors.
3. **Hardcoded Dashboard Topology**: We initially assumed the dashboard magically knew the 4 microservices. Rejected. We implemented a dynamic topological discovery step via Jaeger's dependency API to formally prove integration.
4. **Redundant RCA Scanning**: We originally had the RCA engine ignore the Alertmanager's hint and scan *all* traces to find the failure. Rejected. Alertmanager already knows which node failed; passing the `service` identity forward to RCA reduces query times from seconds to milliseconds.

---

## 10. FINAL TECH STACK

| Component | Technology | Role |
| :--- | :--- | :--- |
| **Orchestration** | Docker Compose | Runs the microservices, OTel pipelines, and engines locally. |
| **Load & Chaos** | Locust | Generates background HTTP traffic and triggers explicit `/fault` endpoints. |
| **Telemetry Router** | OpenTelemetry Collector | Receives all OTLP signals and routes them to storage backends. |
| **Metrics Engine** | Prometheus + Alertmanager | Stores time-series data and pushes primary deterministic webhooks. |
| **Logs Engine** | Grafana Loki | Aggregates structured logs for targeted localized RCA queries. |
| **Traces Engine** | Jaeger | Stores distributed request spans and serves the dependency API for the UI. |
| **RCA Engine** | Python 3 + `FastAPI` | Webhook listener that micro-buffers, correlates, and executes rules. |
| **API Control** | `docker-py` | Connects from the RCA container to the host daemon to manipulate infra state. |
| **Dashboard UI** | Next.js / React + Tailwind | Dynamic node graph utilizing Server-Sent Events (SSE) for visceral presentation. |

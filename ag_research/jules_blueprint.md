# Final Jules Execution Blueprint

This document contains the exact prompts and workflow pacing required to safely execute the project via Google's `Jules` coding agent. 

## ⚠️ Global Jules Rules (Universal Prompt Header)
*Paste this at the top of EVERY Jules interaction to guarantee hackathon alignment.*

> **GLOBAL INSTRUCTIONS FOR JULES:**
> 1. **Demo Constraint:** Write ONLY what is needed for a 3-minute demo. Omit production auth, TLS, or persistent DB volumes.
> 2. **Latency Constraint:** The system must respond end-to-end in <15s. Ensure your code executes in <100ms. Do not use heavy ORMs or unneeded bloated layers. Heavily review your code for optimization.
> 3. **Determinism:** Do not use probabilistic ML models unless explicitly secondary. Use strict IF/ELSE rule-matching against explicit JSON payload contracts.
> 4. **Boundary Constraint:** Work EXCLUSIVELY in your assigned directory. Do not drift into modifying other folders.

---

## 🚦 Phase A: Foundation (Parallel Run 1)

**Instance 1 (Microservices & Chaos)**
> "Review the `/sock-shop` directory to understand the base microservice architecture. Do not use the entire monolith. Extract only 4 minimal stateless services (e.g., frontend, auth, cart, payment) into the `/services` folder. Strip out all unnecessary bloat. Expose native REST routing. Critically, you must add explicit chaos endpoints: `/fault/crash`, `/fault/timeout`, and `/fault/error` to the `payment` and `orders` services to simulate failures. These endpoints must genuinely hang or return 500s."

**Instance 2 (OTel & Prometheus)**
> "Work in `/observability`. Set up `prometheus.yml` and an OpenTelemetry Collector configuration. Ensure the Collector scrapes `/metrics` from the 4 services. You must write explicit PromQL Alert rules (e.g., `error_rate > 5%` and `latency > 2s`) and configure Prometheus Alertmanager to POST an HTTP JSON Webhook to an external URL when tripped."

**Instance 3 (Loki & Jaeger)**
> "Work in `/observability`. Set up `loki-config.yaml` and `promtail-config.yaml`. Configure Promtail with an aggressively low `batchwait` (e.g., 100ms) to bypass standard log ingestion latency. Setup a minimal Jaeger instance to accept OTLP traces. Ensure you write docker-compose definitions for these."

🛑 **FAILURE PAUSE 1:** 
*Action:* Wait for Jules Instances 1, 2, and 3 to complete. 
*Validation:* Use a local `docker-compose up` to verify endpoints exist and metrics are visible in raw format. Do not proceed until true.

---

## 🧠 Phase B: Intelligence (Parallel Run 2)

**Instance 4 (Alertmanager & RCA Engine)**
> "Work in `/intelligence`. Write a lightweight Python FastAPI application. It must expose an HTTP endpoint `/alert` to receive structural JSON webhooks from Prometheus Alertmanager containing the key `service`. 
> 1. Upon receiving an alert, the engine must `time.sleep(3)` to wait for log ingestion.
> 2. It must query the Loki API specifically for the failed `service` label to extract the `"root_cause"`.
> 3. It must formulate a JSON remediation payload: `{"action": "restart", "target": "<service>"}`.
> Output this payload to another HTTP hook."

**Instance 5 (Auto-Remediation Docker SDK)**
> "Work in `/remediation`. Write a robust Python service that receives JSON actions. It must mount `/var/run/docker.sock` and use the `docker-py` SDK.
> 1. Implement a Cooldown Cache: If `payment-service` was restarted in the last 30 seconds, IGNORE the command to prevent infinite loops.
> 2. Execute `client.containers.get(target).restart()`.
> 3. POST the finalized action to a Dashboard event sink."

🛑 **FAILURE PAUSE 2:** 
*Action:* Manually cURL a fake Alertmanager JSON payload to `/intelligence/alert`.
*Validation:* Observe if Instance 5 actually executes a docker restart on a local container.

---

## 🖥 Phase C: UI & Integration (Parallel Run 3)

**Instance 6 (React SSE Dashboard)**
> "Work in `/dashboard`. Build a Next.js / React application utilizing Tailwind CSS. 
> 1. Do not use generic polling. Use Server-Sent Events (SSE) to consume a live stream of RCA events.
> 2. On mount, fetch the topology graph from Jaeger's API and draw a force-directed node graph.
> 3. When an SSE event fires, immediately pulse the corresponding node RED, scroll a log entry mentioning the RCA logic, and pulse GREEN upon recovery."

**Instance 7 (Chaos Locust Scripting)**
> "Work in `/chaos`. Write a `locustfile.py`. Generate a constant baseline of HTTP traffic (e.g., 50 req/sec) to the `/services/frontend`. Include a manual trigger or a localized script to hit the `/fault/timeout` chaos endpoints on command. Keep it extremely lightweight."

**Instance 8 (Global Integration & Glue)**
> "Work in `/deploy`. Synthesize the outputs of all previous instances into a single, master `docker-compose.yml` file. Ensure network bindings are correct (e.g., `host.docker.internal` or proper Docker network DNS names for the webhooks). Ensure `/var/run/docker.sock` is explicitly mounted to the remediation container."

🛑 **FAILURE PAUSE 3:** 
*Action:* Run the master deploy file. Push traffic via Locust. Click the UI to trigger a failure.
*Validation:* The 9-second loop perfectly executes in real-time. System is ready for the 3-minute Hackathon presentation.

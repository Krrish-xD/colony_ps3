# V2 Master Testing & Integration Guide

Because v2 is built as a complex distributed system (9 microservices, 5 observability tools, 2 ML models, a remediation engine, and 2 UIs), you **cannot** just `docker compose up` everything at once right out of the gate. 

You need to bring the system up in **layers**, verifying each layer works before adding the next one.

Here is the exact step-by-step master plan to test the v2 architecture once Jules delivers the code.

---

## 🛠️ Layer 1: Infrastructure & Observability (The Foundation)
***Goal:** Ensure the Docker network exists and the core telemetry stack is up, listening, and healthy.*

1. **Create the Network:**
   ```bash
   docker network create colony-net
   ```
2. **Start Observability Stack:**
   ```bash
   cd v2/observability
   docker compose up -d
   ```
3. **Verify Health:**
   - Open Grafana: `http://localhost:3001` (admin/admin). Ensure it loads.
   - Prometheus: `http://localhost:9090/-/ready` (Should say "Prometheus Server is Ready").
   - Jaeger: `http://localhost:16686` (UI should load).

---

## 🧩 Layer 2: Microservices & Telemetry Injection
***Goal:** Ensure the 9 FastAPI services can talk to each other and are properly sending traces/metrics/logs to Layer 1.*

1. **Start Microservices:**
   ```bash
   cd v2/microservices
   docker compose up -d --build
   ```
2. **Verify Inter-Service Communication:**
   - Hit the frontend health endpoint: 
     ```bash
     curl http://localhost:8001/health
     ```
   - Hit the frontend catalog route (which calls downstream `catalog-service`):
     ```bash
     curl http://localhost:8001/catalog
     ```
     You should get a JSON response with items.
3. **Verify Observability Injection:**
   - **Metrics:** Go to Prometheus (`localhost:9090`) and query `http_server_duration_milliseconds_sum`. You should see metrics for `frontend-service` and `catalog-service`.
   - **Logs:** Go to Grafana (`localhost:3001`) -> Explore -> Loki. Run `{app="frontend-service"}`. You should see structured JSON logs.
   - **Traces:** Go to Jaeger (`localhost:16686`). Select `frontend-service` and click "Find Traces". You should see a trace showing the jump from frontend to catalog.

---

## 🚦 Layer 3: Load Generation & Chaos (The Trigger)
***Goal:** Ensure Locust can generate baseline traffic, and that the fault endpoints actually break the system and appear in telemetry.*

1. **Start Locust:**
   ```bash
   cd v2/loadgen
   docker compose up -d --build
   ```
2. **Verify Baseline Traffic:**
   - Go to the Locust UI: `http://localhost:8089`
   - Start a test: 50 users, 5 spawn rate, host: `http://frontend-service:8001`
   - You should see requests flowing and 0% failures.
3. **Chaos Injection Test (CRITICAL):**
   - Leave Locust running.
   - In a terminal, intentionally break the payment service:
     ```bash
     curl http://localhost:8006/fault/timeout
     ```
   - **Watch the fallout:** Go to Grafana/Prometheus. You should see a massive spike in P99 latency. Go to Jaeger, you should see traces with red error icons. This proves the system accurately captures anomalies.
   - Stop Locust traffic. 

---

## 🧠 Layer 4: ML Intelligence (The Brain)
***Goal:** Train the ML models on the telemetry data and verify the RCA engine can catch anomalies.*

1. **Generate Training Data:**
   - Start Locust baseline traffic again.
   - Run the synthetic data generator you wrote:
     ```bash
     python v2/intelligence/training/generate_training_data.py --samples-per-fault 20 --normal-samples 50
     ```
2. **Train the Models:**
   - Run the training scripts (which Jules will provide based on `04_ml_rca_engine.md`).
   - Copy the resulting `.pt` / `.pkl` model weights into `v2/intelligence/models/`.
3. **Start the Intelligence Engine:**
   - Update Alertmanager in `v2/observability/alertmanager.yml` to point webhooks to `http://intelligence:5000/action`. (Restart Alertmanager).
   - Start the engine:
     ```bash
     cd v2/intelligence
     docker compose up -d --build
     ```
4. **End-to-End RCA Test:**
   - Start Locust. Break a service (`curl http://localhost:8007/fault/error`).
   - Check the Intelligence logs (`docker logs v2_intelligence_1 -f`). Within ~1-3 seconds, you should see Alertmanager hit the engine, and the engine outputting a JSON payload with an RCA classification and confidence score!

---

## 🔧 Layer 5: Auto-Remediation (The Hands)
***Goal:** Ensure the remediation engine receives the RCA payload and successfully restarts the failing Docker container instantly.*

1. **Start Remediation Engine:**
   ```bash
   cd v2/remediation
   docker compose up -d --build
   ```
   *(Ensure it mounts `/var/run/docker.sock` so it has permissions).*
2. **Full Closed-Loop Test:**
   - Run Locust.
   - Break the auth service (`curl http://localhost:8002/fault/crash`).
   - **Watch the magic:** 
     1. Locust throws errors.
     2. Intelligence engine logs show RCA detection.
     3. Remediation engine logs show `Received RCA... restarting Auth Service`.
     4. Auth service container restarts (`docker ps` will show it just started).
     5. Locust errors drop back to 0.
   - You just verified the full sub-5-second loop!

---

## 🎥 Layer 6: UI Dashboards (The Face)
***Goal:** Verify the Next.js apps correctly visualize the live system state.*

1. **Start UIs:**
   - Run the Control Center (`v2/loadgen/ui/`) and Main Dashboard (`v2/dashboard/`).
2. **Demo Rehearsal:**
   - Use the Next.js Control Center (Port 4000) to spin up traffic and hit a Chaos Grid button.
   - Look at the Next.js Main Dashboard (Port 3000). You should see the topology map glow red, the SSE event stream populate with the RCA timeline, and the incident card update.

# Final System Architecture

## Full System Flow (End-to-End)
The architecture is designed as a fast, append-only, closed-loop system deployed entirely via Docker Compose.
1. **Traffic Generation**: K6 continuously blasts the microservices array (e.g., frontend, auth, payment) with HTTP requests.
2. **Telemetry Ingestion**: 
   - Applications emit Prometheus metrics (latency/errors/CPU).
   - Promtail tails container logs and immediately pushes them to Loki (sub-second batch waits).
   - Application spans are sent via OTLP directly to the Jaeger collector.
3. **Live Metric Streaming**: Prometheus uses `remote_write` to stream incoming metrics directly into the Detection Engine.
4. **Instant Detection**: A Python service maintains a sliding window of these metrics and passes them through an `IsolationForest` model. If latency spikes beyond the dynamic envelope, it fires an HTTP POST.
5. **RCA & Correlation**: The RCA Python service receives the webhook. It waits 1 second, then queries Loki for explicit error messages linked to the failing service. It extracts the `trace_id` and checks Jaeger for deep dependency failures.
6. **Automated Remediation**: By binding the rule (e.g. `payment-service timeout`) to an action, the RCA service uses the Docker API socket to execute a container restart.
7. **Visualization Update**: The RCA service instantly pushes an Event Annotation to Grafana, placing a distinct vertical line on the timeline to show exactly when the container was bounced.

## Data Movement Pipeline
**(Raw Data)** -> K6 + Microservices -> 
**(Ingestion)** -> Prometheus (Metrics) + Loki (Logs) + Jaeger (Traces) ->
**(Streaming)** -> Prometheus `remote_write` -> 
**(Inference)** -> Python Detection Engine (Isolation Forest) -> 
**(Webhook Payload)** -> Python RCA Engine -> 
**(Queries + Actions)** -> [Loki Query] -> [Docker API Restart] -> [Grafana POST Annotation]

## Tool Stack
- **Infrastructure**: Docker Compose, K6 (Load Testing).
- **Observability**: Prometheus (Time-series), Grafana Loki (Logs), Promtail (Log Collector), Jaeger (Distributed Tracing).
- **Intelligence Layer**: Python 3, `scikit-learn` (Isolation Forest), `FastAPI` (Webhook Listener).
- **Automation / Dashboard**: `docker-py` (Remediation API), Grafana (Visualization & Annotations).

## Latency Strategy (<15s Constraints)
- **Elimination of Polling**: Typical Prometheus setups rely on 15s scrape intervals and downstream 15s polling. We bypass this by utilizing Prometheus `remote_write` directly into the ML engine, shaving off up to 15 seconds.
- **Aggressive Log Flushing**: Promtail is configured with a 100ms `batchwait` to ensure that root cause error logs hit Loki practically simultaneously with the metric spikes hitting Prometheus.
- **Fast Algorithm**: Instead of an LSTM sequentially predicting the next time-step, Isolation Forest is used on sliding window features, pulling inference time down to under ~50ms.
- **Socket-Level Remediation**: Using `/var/run/docker.sock` bypasses network latency and orchestration overhead, allowing the RCA engine to restart containers locally in milliseconds.

## Example Scenario: The Payment Service Crash
1. **Failure State**: A memory leak script causes the `payment-service` to freeze.
2. **Detection (0-2s)**: `payment-service` request latency shoots from 50ms to 5000ms. Prometheus remote writes the data. Isolation Forest flags the anomaly score as `0.95` (critical).
3. **Trigger (2s)**: Detection engine POSTs `{"service": "payment-service", "metric": "latency"}` to the RCA webhook.
4. **RCA Phase (3-5s)**: The RCA engine pauses for 1s. It queries Loki for `app=payment-service` and finds `[ERROR] Connection Pool Exhausted trace_id=xyz`. 
5. **Remediation & Audit (6s)**: RCA matches the error to its rule dictionary, issues a `container.restart()` via the Docker API, and sends an annotation to Grafana: *"Restarted Payment Service due to Pool Exhaustion."*
6. **Result**: Within 10 seconds of the freeze, the service is fresh, metrics stabilize, and the dashboard clearly reflects the entire incident.

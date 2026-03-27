# Problem Breakdown: Real-Time AI Observability System (PS3)

## 1. Microservices Setup
- **Requirement:** Deploy a distributed application (e.g., Sock Shop) with at least 6 services.
- **Environment:** Docker Compose (preferred for 30-hour hackathon).
- **Traffic:** Generate realistic load using k6 or Locust.

## 2. Observability Pipeline
- **Metrics:** Stream to Prometheus (CPU, memory, latency, error rates).
- **Logs:** Stream structured logs to Loki or OpenSearch.
- **Traces:** Stream distributed traces to Jaeger.

## 3. Detection Layer (Anomaly + Logs)
- **Metrics Anomaly Detection:** Train/use lightweight ML (e.g., Isolation Forest) on Prometheus metrics to detect degradation.
- **Log Understanding:** Fine-tune/use a log model (DistilBERT/LogBERT or pattern matching) to classify errors and anomalies.

## 4. Root Cause Engine (RCA)
- **Goal:** Correlate metric spikes, log errors, and trace delays to identify the specific failing service.
- **Approach:** Needs a fast, real-time correlation engine (rule-based or lightweight ML) that suppresses false alerts using confidence thresholds.

## 5. Auto-Remediation Engine
- **SLA:** Detect, attribute, and fix within 15 seconds.
- **Action:** Trigger automated remediations (e.g., restart container, scale service) via Docker/Kubernetes APIs.
- **Audit:** Log every action alongside supporting evidence.

## 6. Dashboard & Visualization (Agent E)
- **Requirement:** Visualize the entire pipeline (metrics, anomalies, RCA output, and remediation actions) in real-time to demonstrate functionality to judges.

## 7. Evaluation & Failure Simulation (Agent G)
- **Requirement:** Systematically inject failures (e.g., kill a service, spike latency) to prove the end-to-end loop works within the 15s SLA and measure success.

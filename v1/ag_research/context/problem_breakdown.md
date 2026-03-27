# Problem Breakdown

## System Pipeline
The system is an end-to-end distributed observability and automated remediation pipeline consisting of five main stages:
1. **Infrastructure**: A microservices application under simulated load (e.g., k6/Locust).
2. **Observability**: Data collection stack gathering Metrics (Prometheus), Logs (Loki), and Traces (Jaeger).
3. **Detection**: Fast anomaly detection layer (Isolation Forest or threshold-based) monitoring metrics to detect when "something is wrong."
4. **RCA + Remediation**: Rule-based intelligence linking metrics spikes with error logs and trace latency to pinpoint the exact failing service, followed by automated remediation via Docker/Kubernetes APIs (restart, scale, reroute).
5. **Dashboard**: Visualization layer displaying the entire flow from anomaly to fix.

## Constraints
- **Latency**: The entire process from failure to detection, RCA, and remediation execution MUST complete within a 15-second window. This requires fast, lightweight models (Isolation Forest) and pre-defined remediation rules over heavy ML generation.
- **Complexity**: Must be hackathon-feasible. Prioritize simplicity and reliable integration over over-engineered ML pipelines.
- **Append-Only Iteration**: All agent-based design updates must be append-only.

## Key Challenges
1. **Correlation**: The hardest technical challenge is effectively linking Prometheus metrics, Loki logs, and Jaeger traces to form a single cohesive root-cause explanation.
2. **Tool Integration**: Juggling the deployment and networking of numerous infra and observability tools.
3. **Real-time execution**: Achieving the 15-second constraint requires near-instant ingestion, fast querying, and immediate API-driven remediation.

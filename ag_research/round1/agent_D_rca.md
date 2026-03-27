# Round 1

## Idea
Use a lightweight Python correlation engine that relies on `trace_id` mapping to link anomalies to root cause logs, followed by execution of simple auto-remediation rules via the Docker socket.

## Approach
- Receive Anomaly trigger (e.g. `payment-service` latency spike).
- Instantly query Jaeger API for the most recent trace involving `payment-service` that exceeds the latency threshold. Extract the `trace_id`.
- Query Loki using the `trace_id` to find explicit error messages (e.g., "DB timeout").
- Rule Engine lookup: `if error == 'DB timeout' and service == 'payment-service' -> ACTION: restart_container`.
- Use the Python `docker` library (via mounted `/var/run/docker.sock`) to execute the restart.

## Assumptions
- Hackathon applications are stateless, making a Docker restart a safe and effective remediation strategy.
- `trace_id` is successfully and uniformly stamped across both Prometheus exemplars and Loki logs.

## Risks
- Mounting the Docker socket in a container gives it root access to the host machine, which is a massive security risk in production (but acceptable for a hackathon demo).
- Querying Jaeger and Loki via API sequentially might add 1-3 seconds to the pipeline.

## Open Questions
- What happens if the root cause is a database outage? Restarting the payment service container won't fix it. Do we need richer remediation rules?

## Evidence / References
- Research emphasizes that trace-to-log correlation (via embedded `trace_id`) is the industry standard for fast RCA. Rule-based auto-remediation via the Docker API is verified as the most pragmatic approach.

## Input Contract
- Anomaly alerts (JSON payloads).
- API access to Loki and Jaeger for correlation.

## Output Contract
- Remediation command executed via Docker socket.
- Diagnosis result sent to Dashboard.

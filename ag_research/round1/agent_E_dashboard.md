# Round 1

## Idea
Build a single, unified Grafana Dashboard "RCA Workbench" that visualizes the entire pipeline: metrics, log correlations, anomaly alerts, and automated actions taken.

## Approach
- Add Prometheus, Loki, and Jaeger as Data Sources.
- Configure Jaeger "Trace to logs" setting to link spans directly to Loki via `trace_id`.
- Create panels:
  1. Top: High-level System Latency and Alert History (Grafana 11.2+).
  2. Middle: Anomaly Scores (metrics custom pushed or pulled).
  3. Bottom: Split view containing Jaeger trace graphs on the left, correlated Loki error logs on the right.
- Add an "Annotations" stream to mark exactly when an Auto-Remediation (e.g., container restart) was triggered.

## Assumptions
- The system will use the newest version of Grafana to leverage the Alert History feature.
- Cross-datasource correlation is configured flawlessly to avoid manual PromQL/LogQL queries during the demo.

## Risks
- High dashboard refresh rates (e.g., every 1 second to meet real-time constraints) might freeze the browser.

## Open Questions
- How does the RCA service (Agent D) push annotations to Grafana to mark the exact moment a remediation occurs?

## Evidence / References
- Research highlights that Grafana natively supports configuring "Trace to Logs" correlations. Annotations are the standard method for marking discrete events like remediation on time-series graphs.

## Input Contract
- Query access to metrics, logs, traces.
- Push access (Grafana API) for RCA service to log annotations.

## Output Contract
- Unified visual interface for the system flow.

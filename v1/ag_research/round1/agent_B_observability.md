# Round 1

## Idea
Deploy Prometheus, Promtail+Loki, and Jaeger alongside the microservices to collect metrics, logs, and traces. Optimize scrape intervals to ensure the 15-second end-to-end constraint is met.

## Approach
- **Prometheus** for metrics.
- **Loki + Promtail** for log aggregation (Promtail deployed as a docker container tailing `/var/lib/docker/containers`).
- **Jaeger** for distributed tracing, capturing OpenTelemetry signals.
- **Crucially:** Prometheus scrape interval will be reduced from the default 15s to 2s to allow near real-time ingestion, reducing pipeline latency.

## Assumptions
- OTLP (OpenTelemetry Protocol) auto-instrumentation will capture sufficient span data without manual SDK logging.
- Storage disk IO limits won't be hit with a 2s scrape interval for the duration of the hackathon demo.

## Risks
- A 2s scrape interval on Prometheus might cause high CPU/memory usage on the observability stack itself.
- Log latency—writing logs to Loki might take a few seconds, breaking the 15s correlation window if RCA is dependent on immediate log availability.

## Open Questions
- Is OpenTelemetry auto-instrumentation enough to inject `trace_id` into application logs automatically?

## Evidence / References
- Research strongly recommends the Prom/Loki/Jaeger combo. Real-time latency ingestion depends entirely on scrape intervals and pull-based model configurations in Prometheus.

## Input Contract
- Raw telemetry (Metrics, Logs, Traces) from Infra.

## Output Contract
- Queryable time-series metrics (PromQL).
- Queryable Logs mapping to trace IDs (LogQL).
- Distributed request spans.

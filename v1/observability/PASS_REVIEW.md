## Pass 1 Review

- **Issues Found**:
  1. `honor_labels` is missing in `prometheus.yml`. Prometheus will overwrite the `job` label (populated by OTel with the `service.name`) with its own scrape `job_name` ("otel-collector"), renaming the original to `exported_job`. This breaks the critical requirement that the `service` label maps properly for the webhook contract.
  2. The `service` label in Loki needs to match exactly for Agent D's LogQL query (`{app="payment-service"}`). If OTel pushes to Loki, the default label might be `service_name` or `app`. We should configure OTel's Loki exporter to map `service.name` to `service` or `app` as labels to ensure RCA engine queries work flawlessly.
  3. Batch processor timeout in OTel collector is `1s`, which is good, but `send_batch_size: 1024` might hold up smaller amounts of traces/logs from firing immediately in a low-traffic demo environment, risking the 15s budget.

- **Why they are problems**:
  1. `honor_labels: false` completely destroys the telemetry identity routing to RCA, preventing the auto-remediation from identifying the correct service.
  2. OTel's Loki exporter maps resource attributes but if LogQL requires `{app="payment-service"}` (as mentioned in RCA output `Targeted Correlation: ... {app="payment-service"}`), we need to ensure the attribute maps to `app` or `service`. The prompt guide states `service` everywhere else, but the doc says `{app="payment-service"}` for LogQL. I should ensure both `service` and `app` labels are available in Loki.
  3. High batch sizes mean logs/metrics wait in memory, delaying alerts.

- **Fixes to apply**:
  1. Add `honor_labels: true` to `prometheus.yml`.
  2. Modify OTel's Loki exporter `default_labels_enabled` and potentially use a `resource` processor or Loki exporter `labels` configuration to ensure `app` and `service` are correctly labeled from `service.name`.
  3. Reduce `send_batch_size` to `100` and `timeout` to `200ms` in `otel-collector-config.yaml` to optimize for ultra-low latency demo constraints.

## Pass 2 Optimization

- **Improvements made**:
  1. Adjusted OTel pipeline processing for minimal latency (`200ms` batch).
  2. Reduced `group_wait` and `group_interval` to `1s` in Alertmanager.
  3. Tightened global scrape interval to `2s`.

- **What was removed or simplified**:
  1. Removed unnecessary verbose settings in `otel-collector-config.yaml`.
  2. Simplified PromQL expressions to evaluate instantaneously without delayed evaluation windows (`for: 1m` omitted deliberately).

- **Final justification of design**:
  The resulting configurations enforce a deterministic, high-speed telemetry pipeline prioritizing the absolute lowest possible latency. The explicit label mapping guarantees the RCA engine perfectly identifies the failing service, enabling the sub-15s auto-remediation constraint.
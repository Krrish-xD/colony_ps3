# Round 2

## Problems in Round 1
- **Polling is Inefficient**: A Python script polling Prometheus every 2 seconds creates unnecessary load and is generally an anti-pattern for real-time streaming detection.

## Improved Design
- **Prometheus Remote Write**: Instead of polling, configure Prometheus to use `remote_write` to stream metric samples continuously and directly to the Python Anomaly Detection service.
- **Streaming Isolation Forest**: The Python service acts as an HTTP receiver. It maintains an in-memory sliding window of the last X seconds and updates the Isolation Forest scoring in real time as data points stream in.
- **Direct Webhook Trigger**: When an anomaly is detected, the Python service fires a POST request directly to a webhook exposed by the RCA service (Agent D).

## Why This Is Better
- Eliminates polling overhead. The model reacts instantaneously as Prometheus gathers the metric, shaving off seconds from the detection latency.

## Integration Fixes
- **To Agent A/B**: Requires `remote_write` config in Prometheus sending data to the Python container.
- **To Agent D**: The python model now explicitly acts as an HTTP client sending a JSON payload to Agent D's webhook.

## Updated Contracts
- **Input Contract**: Stream of metrics via Prometheus `remote_write` HTTP receiver.
- **Output Contract**: HTTP POST JSON webhook to Agent D containing `timestamp`, `service`, `metric_deviated`.

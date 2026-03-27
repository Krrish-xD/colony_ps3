# Round 1

## Idea
A standalone Python service that continuously queries Prometheus metrics, running a fast Anomaly Detection using `scikit-learn`'s Isolation Forest algorithm.

## Approach
- Build a Python script using `prometheus-api-client` to poll Prometheus every 2 seconds.
- Monitor specific golden signals: Request Latency and Error Rate.
- Apply a pre-trained or iteratively trained Isolation Forest model on the incoming time-series window.
- If the anomaly score breaches a threshold, an HTTP POST payload is instantly sent to the RCA Engine.

## Assumptions
- Isolation Forest inference is virtually instantaneous (sub 100ms) on a small subset of metric features.
- We can hardcode the model to only monitor standard HTTP metrics to save computation.

## Risks
- Polling Prometheus every 2 seconds might be inefficient. 
- The model might flag normal traffic bursts from K6 as anomalies (high false positive rate) if it is not tuned correctly.

## Open Questions
- Should the Python anomaly detector push the anomaly scores back to Prometheus as a custom metric, or solely send events to the RCA engine?

## Evidence / References
- Research confirms Python + Isolation Forest is highly effective for time-series anomaly detection and is computationally lightweight compared to LSTM architectures, fitting the sub-15s requirement perfectly.

## Input Contract
- Real-time structured metrics stream (via PromQL API queries or exported metrics).

## Output Contract
- JSON anomaly alert payload (`timestamp`, `service`, `metric_deviated`).

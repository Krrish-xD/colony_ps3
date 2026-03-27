# Round 2

## Problems in Round 1
- **Race Condition with Logs**: If Agent D queries Loki immediately after receiving an anomaly alert, the logs might not have been ingested yet due to processing latency.
- **Missing Dashboard Integration**: Agent D didn't have a mechanism to tell the Dashboard (Agent E) that a remediation action took place.

## Improved Design
- **Webhook Listener**: Implement a lightweight FastAPI server to receive the anomaly webhook from Agent C.
- **Wait-and-Retry Correlation Loop**: Upon receiving the alert, Agent D waits 1 second, then queries Loki. If no logs are found, it retries every 1 second (up to 3 times) before falling back to a generic restart or failing.
- **Grafana Annotation API**: After successfully executing a Docker restart via the socket, Agent D uses the Grafana HTTP API to POST an annotation to the Dashboard. 

## Why This Is Better
- The retry loop makes the RCA engine extremely robust to minor pipeline jitters and ingestion delays.
- The Grafana annotation closes the loop, providing the user visual confirmation of the exact moment the RCA engine took action.

## Integration Fixes
- **From Agent C**: Now explicitly running a web server to receive the trigger.
- **To Agent E**: Uses standard Grafana Annotation API endpoints.

## Updated Contracts
- **Input Contract**: HTTP Webhook listener on `/alert` accepting JSON anomaly payloads. Query access to Loki/Jaeger.
- **Output Contract**: Docker socket commands. HTTP POST to Grafana Annotations API (`/api/annotations`) with event details.

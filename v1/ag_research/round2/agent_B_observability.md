# Round 2

## Problems in Round 1
- **Log Ingestion Delay**: Promtail/Loki might delay logs by a few seconds compared to Prometheus metrics. This breaks immediate correlation by the RCA engine.

## Improved Design
- **Optimized Promtail Config**: Configure Promtail to push logs to Loki instantaneously by aggressively tuning `batchwait` (e.g., set to 100ms instead of default 1s) and `batchsize`.
- **Aligning Timestamps**: Ensure all services log explicitly in JSON format with precise timestamps, and configure Loki to extract and use the application timestamp rather than the Promtail ingestion timestamp. This guarantees that even if logs arrive late, their logical time matches the metric spike perfectly.

## Why This Is Better
- Tuning `batchwait` drastically reduces ingestion latency, preserving the 15-second end-to-end constraint. Extracting JSON timestamps guarantees that out-of-order logs won't break the correlation logic.

## Integration Fixes
- None needed, just internal configuration tuning.

## Updated Contracts
- **Output Contract**: Logs guaranteed to be ingest-available within <1 second of emission, logically ordered by precise application timestamps.

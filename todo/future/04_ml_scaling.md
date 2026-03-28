# Future: Scale ML Models for 4-Machine Cluster

When distributing across the 4-machine cluster:

## Machine Assignment
- **i5-12H + RTX 3050 (Linux)**: Dedicated ML inference node
- **M5 (macOS, 16GB)**: Observability stack
- **i5-11th (Windows, 16GB)**: 9 Microservices + Locust
- **M3 (macOS, 8GB)**: Dashboard + Control Panel

## Model Upgrades

### Log Classifier: MiniLM → DistilBERT
- Swap `all-MiniLM-L6-v2` (22MB, 384-dim) for `distilbert-base-uncased` (256MB, 768-dim)
- Fine-tune on the collected training data (not just frozen embedding)
- Update FusionClassifier input_dim: 768 + 8 + 6 = 782
- Retrain classifier head
- Expected: better semantic understanding, ~15ms inference on RTX 3050

### Metric Detector: LSTM → TCN
- Swap LSTM(hidden=64) for Temporal Convolutional Network
- TCN handles longer sequences better and trains faster
- Can monitor all 9 services simultaneously instead of round-robin

### Add LogBERT for Anomaly Detection
- Pre-train on normal logs, detect deviations as anomalies
- Runs as secondary detector alongside DistilBERT classifier

## Network Config
- Intelligence engine exposes port 5000 on LAN
- Alertmanager on M5 points to `<i5-12H-LAN-IP>:5000`
- Remediation engine also on i5-12H (same machine has Docker socket)

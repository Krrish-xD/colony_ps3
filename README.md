# Real-Time AI Observability System (PS3)

## 🎯 Problem Statement
**"Build a real-time AI observability system that ingests live logs and metrics from an actually running distributed application, performs root cause analysis using ML, and triggers automated remediations end to end under 15 seconds."**

### Core Requirements:
- **Target Application:** Deploy a distributed app (e.g., Sock Shop, Online Boutique, or custom stack) with at least 6 services using Docker Compose or Kubernetes.
- **Load Generation:** Simulate real traffic using k6 or Locust.
- **Observability Stack:** 
  - Logs ➡️ Loki/OpenSearch
  - Metrics ➡️ Prometheus
  - Traces ➡️ Jaeger
- **AI/ML Layer:** 
  - Fine-tune a log model (DistilBERT/LogBERT) for anomaly detection.
  - Train an LSTM/TCN on Prometheus metrics for degradation detection.
  - Correlate log, metric, and trace anomalies to identify the true root-cause service.
- **Auto-Remediation:** Trigger automated fixes via Docker/Kubernetes APIs or alerting integrations within 15 seconds.
- **Reliability:** Use confidence thresholds to suppress false alerts and log every action alongside supporting evidence.

---

## 🧠 System Overview
A closed-loop system that **watches a running app ➡️ detects anomalies ➡️ pinpoints the exact root cause ➡️ applies a fix autonomously in <15s**.

### Data Sources (The 3 Pillars)
1. **Metrics (Prometheus):** CPU usage, memory, latency, and error rates. Good for detecting *"something is wrong"*.
2. **Logs (Loki/OpenSearch):** Error messages, stack traces, and warnings. Good for understanding *"what went wrong"*.
3. **Traces (Jaeger):** Request paths across services. Good for pinpointing *"where exactly the problem is"*.

---

## 🏗️ Architecture Flow

```text
[Load Generator (k6/Locust)]
        ↓
[Microservices (6+ on Docker Compose / K8s)]
        ↓
 ┌───────────────┬───────────────┬───────────────┐
 │ Prometheus    │ Loki          │ Jaeger        │
 │ (Metrics)     │ (Logs)        │ (Traces)      │
 └──────┬────────┴──────┬────────┴──────┬────────┘
        ↓               ↓               ↓
        [Anomaly Detection + RCA Engine]
                        ↓
              [Decision Engine]
                        ↓
        [Auto Remediation (Docker/K8s API)]
```

---

## 🚀 Implementation Strategy (30-Hour Hackathon Approach)

Given the strict 30-hour time limit, the primary goal is an **end-to-end working pipeline**. We will prioritize a functional, correlated system over complex, computationally heavy ML perfection.

### Phase 1: Infrastructure & Observability (Current Focus)
- Deploy a sample microservices app (e.g., Sock Shop) using Docker Compose (easier and faster than K8s).
- Set up Prometheus (metrics), Loki (logs), and Jaeger (traces).
- Verify data ingestion before introducing AI.

### Phase 2: Anomaly Detection (The ML Layer)
- **Metrics:** Start with fast models like Isolation Forest (or simplified thresholds) before attempting LSTM.
- **Logs:** Implement basic error classification (can use DistilBERT if time permits, or fallback to smart pattern matching).

### Phase 3: Root Cause Analysis (RCA) - *The Hard Part*
- Implement rule-based or lightweight ML correlation. 
- Example Logic: `metrics spike (high latency) + logs show DB timeout + trace delays in payment-service = Root cause is payment-service`.

### Phase 4: Auto-Remediation (<15s SLA)
- Map identified root causes to predefined actions:
  - Service crash ➡️ `Restart container`
  - High load ➡️ `Scale service`
- Execute these actions programmatically via the Docker API.

---
*Hackathon project - 30 hours on the clock.*
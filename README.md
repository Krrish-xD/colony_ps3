# Real-Time AI Observability System (PS3)

## 🎯 Problem Statement
**"Build a real-time AI observability system that ingests live logs and metrics from an actually running distributed application, performs root cause analysis using ML, and triggers automated remediations end to end under 15 seconds."**

> **Note:** The full, authoritative architectural breakdown, latency strategies, and component designs for this project can be found in [`ag_research/final_system_guide.md`](./ag_research/final_system_guide.md).

### Core Requirements:
- **Target Application:** Deploy a distributed app (4 independent services) with Docker Compose.
- **Load Generation & Chaos:** Simulate real traffic and inject failures using Locust.
- **Unified Telemetry:** Route all signals through an OpenTelemetry (OTel) Collector to Prometheus (Metrics), Loki (Logs), and Jaeger (Traces).
- **Detection & RCA:** 
  - Push-based anomaly triggers via Prometheus Alertmanager.
  - Targeted LogQL correlation within a 3-second micro-buffer to bypass ingestion latency.
- **Auto-Remediation:** Trigger container restarts via Docker socket under 15 seconds with a 30s cooldown cache.
- **Dashboard:** Custom Next.js/React UI updating via Server-Sent Events (SSE).

---

## 🧠 System Overview
A closed-loop system that **watches a running app ➡️ detects anomalies ➡️ pinpoints the exact root cause ➡️ applies a fix autonomously in <15s**.

### Data Sources (The 3 Pillars)
1. **Metrics (Prometheus):** CPU usage, memory, latency, and error rates. Good for detecting *"something is wrong"*.
2. **Logs (Loki):** Error messages, stack traces, and warnings. Good for understanding *"what went wrong"*.
3. **Traces (Jaeger):** Request paths across services. Good for pinpointing *"where exactly the problem is"*.

---

## 🏗️ Architecture Flow

```text
[Locust Traffic & Chaos Generator]
         ↓
[Microservices (4 nodes on Docker Compose)]
         ↓
  [OpenTelemetry Collector]
         ↓
 ┌───────────────┬───────────────┬───────────────┐
 │ Prometheus    │ Loki          │ Jaeger        │
 │ (Metrics)     │ (Logs)        │ (Traces)      │
 └──────┬────────┴──────┬────────┴──────┬────────┘
        ↓               ↓               ↓
 [Alertmanager]  [Loki Targeted Query]  [Topology API]
        ↓               ↓               ↓
   [Python Root Cause Analysis & Remediation Engine]
                        ↓
     [Auto Remediation (Docker Socket API)]
                        ↓
       [Next.js React Dashboard (via SSE)]
```

---

## 🚀 Implementation Strategy (30-Hour Hackathon Approach)

Given the strict 30-hour time limit, the primary goal is an **end-to-end working pipeline**. We prioritize a highly functional, deterministic, and correlated system.

### Phase 1: Infrastructure & Observability (Next Up)
- Deploy the 4 sample microservices + Locust load generator using Docker Compose.
- Set up the OTel Collector, Prometheus, Loki, and Jaeger.
- Verify data ingestion and topology.

### Phase 2: Detection Layer 
- Write deterministic PromQL alert rules for the microservices.
- Configure Alertmanager to push webhooks when latency or error rates spike.

### Phase 3: Root Cause Analysis (RCA) - *The Hard Part*
- Build the Python webhook listener.
- Implement the 3-second micro-buffer and targeted Loki query (`{app="failed-service"}`).
- Implement the 30-second cooldown cache to prevent restart loops.

### Phase 4: Auto-Remediation & Dashboard (<15s SLA)
- Map identified root causes to predefined actions (Docker socket restart).
- Build the Next.js Dashboard to dynamically discover topology from Jaeger and stream events via SSE.

---
*Hackathon project - 30 hours on the clock.*
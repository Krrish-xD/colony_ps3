# 🚀 v2 Architecture Roadmap

This document outlines the transition from our successful `v1` hackathon demo to a robust, production-grade `v2` implementation of the Distributed Observability & Auto-Remediation System.

---

## 🏗️ 1. What We Built (The `v1` Foundation)

`v1` successfully proved the core concept: a closed-loop system capable of detecting anomalies, analyzing root causes, and executing remediation in **under 15 seconds**.

**What you should take and reuse:**
*   **The Observability Backbone**: We perfectly tuned the `otel-collector → Prometheus / Loki / Jaeger` pipeline. The aggressive `2s` scrape intervals, custom label mappings (`job` → `service`), and Loki's `100ms` flush thresholds are gold. Keep these entirely.
*   **The Event-Driven Topology**: The Alertmanager → RCA Webhook (`http://intelligence/alert`) pattern is incredibly fast and reliable. Keep this event-routing architecture.
*   **The UI Streaming Mechanism**: The Next.js Next/SSE (Server-Sent Events) pipeline works flawlessly for real-time dashboard updates without WebSocket overhead. Keep this.

---

## 🛠️ 2. What We Need to Improve (The Upgrades)

`v1` took deliberate shortcuts to guarantee a flawless 15-second live demo. `v2` needs to replace these shortcuts with production-ready logic.

*   **Remove the `3-second sleep` hack:** In `v1`, the RCA engine blindly waits 3 seconds to let Loki ingest the logs. In `v2`, replace this with a **retry-backoff mechanism** or a **tailing log stream** (e.g., Loki WebSocket tailing) so the RCA engine analyzes logs the millisecond they arrive.
*   **Decouple Docker Socket Dependency:** `v1` mounts `/var/run/docker.sock` to restart containers. This is a massive security risk in production. `v2` must interact with a real orchestration layer (e.g., Kubernetes API, Nomad API, or AWS ECS/EKS).
*   **True Service Topology discovery:** `v1` hardcodes the topology nodes (`payment-service`, `cart-service`, etc.) in the dashboard if Jaeger fails. `v2` should continuously poll the Jaeger API (`/api/services`) to dynamically draw the architecture graph in real time as services scale up or down.

---

## 🌟 3. What New Things to Build (The `v2` Expansions)

Here is where `v2` steps away from being a "hackathon project" and becomes an enterprise-grade AI observability pipeline:

### 🧠 A. ML Classifier based Root Cause Analysis
*   **The Gap:** `v1` uses hardcoded `if/else` checks (e.g., `if "timeout" in log -> DB Timeout`).
*   **The Build:** Step away from slow/dumb local LLMs. Build a fast, specialized **Text Classification Engine** using `Sentence Transformers` (e.g., `all-MiniLM-L6-v2`) combined with a lightweight classifier (like Logistic Regression or a small feed-forward neural net).
*   **How:** 
    1. **Log Formatting:** Redesign the logging structure across all microservices so the payload is highly optimized for vector embeddings (e.g., removing noise, keeping semantic failure reasons distinct).
    2. **Inference Pipeline:** When Alertmanager fires, the Intelligence engine pulls the last N logs, generates embeddings in milliseconds, and classifies them into distinct failure categories (e.g., `db_timeout`, `memory_leak`, `normal_operation`) with actual softmax confidence scores.

### 🗄️ B. Stateful Data Layer & Real Failures
*   **The Gap:** `v1` services are stateless and use `os._exit(1)` to mock failures.
*   **The Build:** Inject a real PostgreSQL database and Redis cache behind the `payment` and `cart` services.
*   **How:** Write chaos scripts that don't just kill containers, but actually exhaust DB connection pools, lock SQL tables, or corrupt Redis cache partitions. The RCA engine must trace the failure all the way down to the specific SQL query.

### 🛡️ C. Multi-Agent Remediation Approvals (Human-in-the-loop)
*   **The Gap:** `v1` blindly restarts the container if confidence > 50%.
*   **The Build:** Implement an approval workflow for destructive actions (e.g., "Roll back database" vs "Restart container").
*   **How:** If confidence is high (>90%), auto-execute. If confidence is medium (50-90%), the system sends a Slack/Discord webhook with a button: *"Anomaly detected: Suspected DB lock. Recommend killing PID 432. [Approve] / [Deny]"*.

### 📊 D. Centralized Rules Management UI
*   **The Gap:** `v1` PromQL rules are hardcoded in `rules.yml`.
*   **The Build:** Add a configuration tab to the Next.js Dashboard.
*   **How:** Allow users to write and deploy new PromQL custom alerting thresholds directly from the UI, which writes to the Prometheus hot-reload API dynamically.

---

## 🗺️ Suggested Next Step for v2

If you want to begin `v2` immediately, the most logical first step is **Step B: The Stateful Data Layer**. 

Adding a real database forces the observability pipeline to ingest more complex traces (DB spans) and proves the system can find RCA beyond simple container crashes.

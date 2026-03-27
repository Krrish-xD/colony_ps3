# PS3: Real-Time AI Observability & Auto-Remediation System

## 1. The Core Objective (The Original PS3 Problem Statement)
Based on the Manipal Institute of Technology (Bengaluru) hackathon prompt, the fundamental goal of this project is to build an **autonomous, self-healing infrastructure managed by AI**. 

The strict constraint that defines this challenge is **latency**: the entire loop—from the moment a microservice fails to the moment the system detects it, analyzes the root cause with Machine Learning, and automatically fixes it—must happen in **under 15 seconds**.

### The Explicit Requirements:
1. **The Target Environment**: Deploy a distributed microservice application (minimum 6 services) using Docker Compose or Kubernetes, under continuous simulated traffic (via Locust or k6).
2. **The Observability Pipeline**: Stream live structured logs to Loki, metrics to Prometheus, and distributed traces to Jaeger.
3. **The ML AI Layer (The Brain)**: 
   - Fine-tune a transformer model (**DistilBERT** or **LogBERT**) to perform anomaly detection on the live log streams.
   - Train a time-series model (**LSTM** or **TCN**) on the Prometheus metrics to detect slow system degradation.
   - Correlate the anomalies across logs, metrics, and traces to pinpoint the exact root-cause service.
4. **Automated Remediation**: Once the AI hits a high confidence threshold, automatically trigger a fix via Docker/Kubernetes APIs (e.g., restarting a container), logging all evidence.

---

## 2. Where We Are Now (The `v1` MVP)
Our `v1` architecture (currently archived in the `/v1` folder) successfully built the entire end-to-end scaffolding and proved that the **sub-15-second latency budget is mathematically possible**.

**What `v1` Accomplished:**
*   Built a custom 4-tier microservice stack (Frontend, Auth, Cart, Payment) instrumented perfectly with OpenTelemetry.
*   Setup head-less Locust scripts to generate continuous healthy traffic and inject intermittent chaos faults.
*   Successfully deployed the full telemetry backbone: Prometheus (metrics), Loki (logs), Jaeger (traces).
*   Built an ultra-fast Alertmanager → RCA Webhook → Remediation API pipeline that successfully restarts failing Docker containers and streams the event to a custom Next.js UI in ~9-12 seconds.

**The `v1` Compromise:**
Because 15 seconds is an incredibly tight window, `v1` bypassed the heavy Machine Learning requirements. Instead of DistilBERT or LSTMs, `v1` used deterministic `if/else` string-matching on the logs (e.g., `if "timeout" in log -> Restart`). This guaranteed a flawless live demo but technically falls short of the ML constraints in the prompt.

---

## 3. The Path Forward (`v2` ML Implementation)
To fully satisfy the PS3 problem statement and win the technical evaluation, `v2` must replace the `v1` deterministic rules with actual trained Machine Learning models while maintaining the sub-15s execution time.

### Step 1: LogBERT / DistilBERT Log Classification
As you suggested, we will build a fast Text Classification Engine. 
*   **The Plan**: We will format our microservice logs into dense, semantic structures.
*   **The Model**: We will take a lightweight Sentence Transformer (like `all-MiniLM-L6-v2`) or fine-tune DistilBERT.
*   **The Execution**: When a metric spikes, the RCA engine will extract the last 50 logs, embed them through the transformer, and run them through a classification head to output the root cause (e.g., "DB Timeout", "Memory Leak") with an explicit confidence score (e.g., `0.94`).

### Step 2: LSTM / TCN Metric Degradation (Optional but required by prompt)
*   **The Plan**: Instead of relying solely on Prometheus static threshold alerts (e.g., `latency > 2s`), we need a lightweight LSTM (Long Short-Term Memory) or TCN (Temporal Convolutional Network) model that continuously ingests the `http_request_duration_seconds` metric.
*   **The Execution**: The model predicts the expected latency for the next 5 seconds. If the actual latency deviates significantly from the LSTM's prediction, it flags an anomaly and triggers the LogBERT engine to find *why*.

### Step 3: Expanding the Microservice Stack
The prompt specifies "at least six services." Our custom stack currently has 4. In `v2`, we need to add 2 more lightweight services (e.g., an `Inventory-Service` and a `Notification-Service`), or simply deploy the open-source **Google Online Boutique** stack and instrument it.

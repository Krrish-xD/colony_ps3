# 🟣 PS3 — Deep Breakdown (what you’re actually building)

## 🧠 One-line meaning

A system that:
**watches a running app → detects something is wrong → figures out exactly where → fixes it automatically in <15s**

---

# 🔩 System Flow (end-to-end)

### 1️⃣ Generate a real system

* 6+ microservices (frontend, auth, cart, payment, etc.)
* Running on:

  * Docker Compose (easier) ✅
  * or Kubernetes (harder)

👉 You simulate real traffic using:

* k6 / Locust

---

### 2️⃣ Collect 3 types of data

## 📊 Metrics (Prometheus)

![Image](https://img.site24x7static.com/images/prometheus-and-grafana-img.svg)

![Image](https://i.sstatic.net/Qr7St.png)

![Image](https://s3.amazonaws.com/a-us.storyblok.com/f/1022730/907b45a1bf/prometheus-histograms-in-grafana.png)

* CPU usage
* Memory
* Request latency
* Error rates

👉 Good for detecting **“something is wrong”**

---

## 📜 Logs (Loki / OpenSearch)

![Image](https://grafana.com/media/docs/loki/get-started-drill-down.png)

![Image](https://cdn.prod.website-files.com/626a25d633b1b99aa0e1afa7/6919cf4a9abca8dab39a5353_1%20%281%29.jpg)

![Image](https://cdn.sanity.io/images/z7wg6mcy/production-2025/67b53593e8c1c8bc728deab50137b6180cc04e0c-2448x1658.png)

* Error messages
* Stack traces
* Warnings

👉 Good for understanding **“what went wrong”**

---

## 🔗 Traces (Jaeger)

![Image](https://www.dash0.com/_next/image?q=100\&url=https%3A%2F%2Fcdn.sanity.io%2Fimages%2Frdn92ihu%2Fproduction%2F274754e59dec648e1659a40ed47f6b8b487219a6-3360x1859.png%3Fw%3D3360%26h%3D1859%26fit%3Dmax%26auto%3Dformat\&w=3840)

![Image](https://timescale.ghost.io/blog/content/images/2022/12/Jaeger-Tracing-with-SPM_hero--1-.png)

![Image](https://openobserve.ai/assets/5_otel_diagram_7927309c74.png)

* Shows request path across services
* Helps identify slow/broken service

👉 Good for **“where exactly the problem is”**

---

# 🤖 3️⃣ ML Layer (core intelligence)

### A. Anomaly Detection

* Input: metrics (time-series)
* Models:

  * Isolation Forest (fast) ✅
  * LSTM (harder)

👉 Output:
“Something abnormal happening”

---

### B. Log Understanding (optional but impressive)

* Use NLP model (DistilBERT)
* Classify logs:

  * normal vs error
  * type of failure

👉 Output:
“Database connection error” / “timeout” etc.

---

### C. Root Cause Analysis (THE HARD PART)

Combine:

* metrics spike
* logs errors
* traces path

👉 Example reasoning:

* latency ↑
* logs show DB timeout
* trace shows delay in `payment-service`

➡️ Root cause = **payment-service**

---

# ⚡ 4️⃣ Auto-Remediation

Once root cause is found:

| Issue           | Action            |
| --------------- | ----------------- |
| Service crash   | Restart container |
| High load       | Scale service     |
| Slow dependency | Reroute / retry   |
| Memory leak     | Restart           |

👉 Done via:

* Docker API / Kubernetes API

---

# ⏱ 5️⃣ 15-second constraint

This is mostly **for judging impact**, not strict enforcement.

To achieve:

* Use **fast models (Isolation Forest)**
* Predefine rules for actions

---

# 🧩 What makes PS3 hard

## 🔴 1. Correlation problem

Not just detecting anomaly — but linking:

* metrics ↔ logs ↔ traces

👉 This is where most teams fail

---

## 🔴 2. Too many tools

You’re juggling:

* Prometheus
* Loki
* Jaeger
* ML model
* Microservices

---

## 🔴 3. Real-time requirement

Pipelines must be fast:

* ingestion → detection → action

---

# 🧪 What a GOOD hackathon version looks like (important)

You **DO NOT need full ML sophistication**

## ✅ Smart simplified version:

### ✔️ Detection

* Use simple threshold OR Isolation Forest

### ✔️ Root cause

* Rule-based:

  * if latency high + error logs in service X → blame X

### ✔️ Fix

* Restart container / scale

👉 Judges care about:

* pipeline working end-to-end
* not perfect ML

---

# 🏗 Minimal Architecture (recommended)

```
[Load Generator]
        ↓
[Microservices (Docker)]
        ↓
 ┌───────────────┬───────────────┬───────────────┐
 │ Prometheus    │ Loki          │ Jaeger        │
 │ (metrics)     │ (logs)        │ (traces)      │
 └──────┬────────┴──────┬────────┴──────┬────────┘
        ↓               ↓               ↓
        [Anomaly Detection + RCA Engine]
                        ↓
              [Decision Engine]
                        ↓
              [Auto Remediation]
```

---

# ⚖️ Realistic Difficulty Breakdown

| Part                | Difficulty |
| ------------------- | ---------- |
| Microservices setup | 6/10       |
| Observability stack | 7/10       |
| ML detection        | 5/10       |
| Root cause logic    | 9/10 🔥    |
| Automation          | 6/10       |

---

# 🏁 How to approach (first step only)

Start with **THIS ONLY**:

👉 Run a simple microservices app + Prometheus
👉 Confirm you can see metrics dashboard

**Don’t touch ML yet**

---

If you want next step, say:
➡️ “next step” and I’ll guide you step-by-step without overload

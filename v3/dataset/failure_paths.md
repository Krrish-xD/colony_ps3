# System Overview

The v3 architecture consists of 9 microservices simulating an e-commerce platform.

**Microservices:**
- `frontend`: User-facing gateway interacting with all domain services.
- `auth`: Handles user login, registration, and token validation.
- `catalog`: Serves product information.
- `cart`: Manages user shopping carts.
- `inventory`: Tracks product stock availability.
- `recommendation`: Suggests related products based on catalog.
- `payment`: Processes user checkouts.
- `shipping`: Calculates shipping rates and routes.
- `notification`: Sends emails/SMS to users for order updates.

**Dependencies Flow:**
```text
frontend
 ├── auth            (Database)
 ├── catalog         (Database)
 ├── cart
 │    └── inventory  (Database)
 ├── recommendation
 │    └── catalog    (Database)
 ├── payment
 │    ├── external-gateway
 │    └── notification
 └── shipping
      ├── external-carrier
      └── notification
```

---

# 2. Service-Wise Failure Modes

### Service: frontend
- **Possible errors:**
  - High error rate (5xx cascading from downstream)
  - Latency spike (waiting on slow downstream)
  - Connection refused (network failure connecting to gateway)
- **Dependencies:** auth, catalog, cart, recommendation, payment, shipping

### Service: cart
- **Possible errors:**
  - Latency spike (waiting on inventory)
  - Service crash (OOM killed)
  - Database deadlock (high error rate)
- **Dependencies:** inventory, redis/database

### Service: inventory
- **Possible errors:**
  - Database connection pool exhaustion
  - High latency (slow SQL query)
  - Crash (bad release)
- **Dependencies:** database

### Service: payment
- **Possible errors:**
  - Dependency failure (external gateway 503)
  - High latency (gateway rate limit)
  - Message broker queue full (notification bottleneck)
- **Dependencies:** external-gateway, notification

### Service: catalog
- **Possible errors:**
  - High error rate (malformed JSON responses)
  - High latency (cache miss storm)
  - Crash (memory leak)
- **Dependencies:** database, cache

### Service: auth
- **Possible errors:**
  - High CPU utilization (token encryption overhead)
  - Database connection timeout (latency)
  - Crash (invalid config mapping)
- **Dependencies:** database

### Service: recommendation
- **Possible errors:**
  - High latency (ML model inference slowdown)
  - Dependency failure (catalog down)
  - High error rate (invalid product IDs)
- **Dependencies:** catalog

### Service: shipping
- **Possible errors:**
  - Dependency failure (external carrier API timing out)
  - High error rate (invalid zip codes / logic bugs)
- **Dependencies:** external-carrier, notification

### Service: notification
- **Possible errors:**
  - Dependency failure (SMTP server down)
  - Service crash (poison pill message in queue)
  - Latency spike (queue buildup)
- **Dependencies:** smtp/sns

---

# 3. Failure Propagation Paths

## Path 1: Inventory Slowdown Cascades to Frontend
- **Trigger:** `inventory` experiences slow database queries. 
- **Path:** `frontend` → `cart` → `inventory`
- **Observed Symptoms:**
  - `frontend` latency increases (wait times out).
  - `cart` latency increases; logs show context deadline exceeded.
  - `inventory` shows high latency but HTTP 200.
- **Root Cause:** `inventory` (latency_spike)

## Path 2: Cart OOM Crash
- **Trigger:** `cart` memory leak causes container restart.
- **Path:** `frontend` → `cart`
- **Observed Symptoms:**
  - `frontend` returns 502 Bad Gateway.
  - `cart` container restart count increases.
  - `cart` logs cut off abruptly.
- **Root Cause:** `cart` (service_crash)

## Path 3: External Payment Target Timeout
- **Trigger:** Third-party payment gateway takes >5s to respond.
- **Path:** `frontend` → `payment` → `external-gateway`
- **Observed Symptoms:**
  - `frontend` checkout times out (504 Gateway Timeout).
  - `payment` latency spikes to 5000ms.
  - `payment` logs show "gateway timeout".
- **Root Cause:** `external-gateway` (dependency_failure)

## Path 4: Catalog Database Connection Failure
- **Trigger:** `catalog` loses connection to its database.
- **Path:** `frontend` → `catalog`
- **Observed Symptoms:**
  - `frontend` returns 500 on product pages.
  - `catalog` error rate spikes to 100%.
  - `catalog` logs show "connection refused: db".
- **Root Cause:** `catalog` (dependency_failure)

## Path 5: Auth Token Validation CPU Exhaustion
- **Trigger:** Traffic spike causes basic `auth` instance to max CPU simulating slow hashing.
- **Path:** `frontend` → `auth`
- **Observed Symptoms:**
  - `frontend` latency increases on login/auth routes.
  - `auth` CPU metrics reach 100%; RPS drops.
  - `auth` logs show "request rejected - max pool sizing".
- **Root Cause:** `auth` (resource_exhaustion)

## Path 6: Recommendation Model Inference Slowdown
- **Trigger:** `recommendation` model loads a unoptimized cold start variant.
- **Path:** `frontend` → `recommendation`
- **Observed Symptoms:**
  - `frontend` product pages load slowly.
  - `recommendation` latency spikes wildly (2000ms+).
  - Trace spans halt on `recommendation` process execution.
- **Root Cause:** `recommendation` (latency_spike)

## Path 7: Notification SMTP Blacklist
- **Trigger:** SMTP provider blocks `notification` outbound IP.
- **Path:** `payment` / `shipping` → `notification` (async/sync)
- **Observed Symptoms:**
  - Order success pages load fine, but queues back up.
  - `notification` error rate spikes exactly to 100%.
  - `notification` logs show `554 Message rejected`.
- **Root Cause:** `notification` (dependency_failure)

## Path 8: Shipping External API Rate Limit
- **Trigger:** Third-party fedex/UPS carrier blocks shipping for 429 Too Many Requests.
- **Path:** `frontend` → `shipping` → `external-carrier`
- **Observed Symptoms:**
  - `frontend` users cannot calculate shipping cost (500).
  - `shipping` error rate spikes.
  - `shipping` logs show `429 Too Many Requests`.
- **Root Cause:** `external-carrier` (dependency_failure)

## Path 9: Frontend Bad Release
- **Trigger:** `frontend` deploys a broken javascript bundle causing logic loops on SSR.
- **Path:** `frontend`
- **Observed Symptoms:**
  - `frontend` CPU metrics peg to 100%.
  - All downstream services see traffic drop to 0.
  - `frontend` logs show missing syntax/module errors.
- **Root Cause:** `frontend` (code_bug)

## Path 10: Inventory Crash Cascades to Cart
- **Trigger:** `inventory` crashes completely.
- **Path:** `frontend` → `cart` → `inventory`
- **Observed Symptoms:**
  - `inventory` instance counts go to 0.
  - `cart` logs show `connection refused to inventory:8080`.
  - `cart` error rate spikes immediately.
- **Root Cause:** `inventory` (service_crash)

## Path 11: Catalog Cache Miss Storm
- **Trigger:** Redis cache for catalog gets purged, all queries hit DB simultaneously.
- **Path:** `recommendation` → `catalog` → `database`
- **Observed Symptoms:**
  - `catalog` latency slowly creeps up over 2 minutes.
  - `recommendation` latency mirrors `catalog` latency.
  - Log features show `cache miss` frequency spiking.
- **Root Cause:** `catalog` (infrastructure_bottleneck)

## Path 12: Notification Poison Pill
- **Trigger:** A malformed payload crashes `notification` parser continuously.
- **Path:** `payment` → message queue → `notification`
- **Observed Symptoms:**
  - `notification` restarts rapidly in a crash loop.
  - `notification` logs show `unmarshal error: invalid type`.
- **Root Cause:** `notification` (poison_pill)

## Path 13: Shipping Bad Config
- **Trigger:** `shipping` service mapping for EU region is missing in config file.
- **Path:** `frontend` → `shipping`
- **Observed Symptoms:**
  - `shipping` specifically throws 400 Validation Error for EU users.
  - Metrics show steady RPS but sharp uptick in 4xx.
  - `shipping` logs show `WARN: unknown region EU`.
- **Root Cause:** `shipping` (config_error)

## Path 14: Recommendation Cascading from Catalog Failure
- **Trigger:** `catalog` crashes.
- **Path:** `frontend` → `recommendation` → `catalog`
- **Observed Symptoms:**
  - `catalog` down (no metrics).
  - `recommendation` logs show `failed to fetch product context from catalog`.
  - `recommendation` error rate spikes simultaneously.
- **Root Cause:** `catalog` (service_crash)

## Path 15: Auth Database Deadlock
- **Trigger:** Multiple concurrent edits lock the `auth` user table.
- **Path:** `frontend` → `auth` → `database`
- **Observed Symptoms:**
  - `auth` latency remains zero, but error rate spikes (aborting queries).
  - `auth` logs show `Deadlock found when trying to get lock`.
- **Root Cause:** `database` (deadlock)

## Path 16: Payment Logic Bug (Zero Total)
- **Trigger:** `payment` service refuses orders with total exactly 0.00.
- **Path:** `frontend` → `payment`
- **Observed Symptoms:**
  - Free items trigger 500s directly on `payment`.
  - Traces halt instantly at `payment` logic blocks.
  - `payment` logs show `validation failed: total must be > 0`.
- **Root Cause:** `payment` (logic_error)

## Path 17: Memory Leak in Frontend
- **Trigger:** `frontend` gradually consumes RAM until killed.
- **Path:** `frontend`
- **Observed Symptoms:**
  - `frontend` Latency creeps up linearly over 30m.
  - Containers eventually restart.
  - Downstreams are totally healthy.
- **Root Cause:** `frontend` (memory_leak)

## Path 18: Notification Latency (SMTP Slowdown)
- **Trigger:** Third-party SMTP takes 10s to accept mail.
- **Path:** `payment` → `notification` → `smtp`
- **Observed Symptoms:**
  - `notification` queue processing latency spikes heavily.
  - Active routines count spikes.
- **Root Cause:** `smtp` (dependency_failure)

## Path 19: Cart Database Disk Full
- **Trigger:** The persistent volume for the `cart` store fills up.
- **Path:** `frontend` → `cart` → `database`
- **Observed Symptoms:**
  - `cart` writes fail instantly.
  - `cart` logs show `no space left on device` or `read-only file system`.
  - Latency is normal (failures are fast).
- **Root Cause:** `database` (infrastructure_failure)

## Path 20: Auth Target Service Timeout
- **Trigger:** Network partition drops packets between `frontend` and `auth`.
- **Path:** `frontend` → network gap → `auth`
- **Observed Symptoms:**
  - `frontend` times out calling auth.
  - `auth` sees NO incoming traffic.
  - Trace spans exist natively on `frontend` but missing `auth` spans.
- **Root Cause:** `network` (partition)

---

# 4. Signal Mapping

For automated ML training to recognize root causes, signals map explicitly:

- **Metrics Pattern**
  - **Latency Spike:** Target service (`latency_ms` > `2000`), upstream services inherit latency.
  - **Error Rate Increase:** Target service (`error_rate` > `0.10`), downstream healthy (rps drops).

- **Log Pattern**
  - **Dependency Failures:** `timeout`, `context deadline exceeded`, `503 Service Unavailable`, `connection refused`.
  - **Crashes:** `exit status 1`, `SIGKILL`, abrupt stops in scrape data.
  - **Resource Issues:** `pool exhausted`, `deadlock`, `too many open files`.

- **Trace Pattern**
  - Trace path defines the impact radius.
  - **Bottleneck Service:** The node in the DAG span with the highest exclusive duration or terminal error tag.

---

# 5. RCA Mapping Table

| Symptom | Metrics | Logs | Trace Bottleneck | Root Cause |
| ------- | ------- | ---- | ---------------- | ---------- |
| Cart API times out | `frontend` auth latency spike | `context deadline exceeded` | `inventory` | `inventory` (latency_spike) |
| Checkout fails completely | `payment` 503 spike, `frontend` errors | `external gateway error` | `payment` | `external-gateway` (dependency) |
| Empty product lists | `frontend` 5xx, `catalog` down | `connection refused` | `catalog` | `catalog` (service_crash) |
| Shipping module blocks checkout | `shipping` 4xx spike | `missing carrier config` | `shipping` | `shipping` (config_error) |
| Login takes 10+ seconds | `auth` high CPU, high latency | `pool exhausted` | `auth` | `database` (resource_exhaustion) |
| Notification delays | `notification` queue backlog metrics spike | `SMTP connection timeout` | `notification` | `smtp` (dependency_failure) |
| Cart throws immediate 500s | `cart` error_rate spikes | `no space left on device` | `cart` | `database` (disk_exhaustion) |
| Recommended items won't load | `recommendation` latency spikes | `timeout fetching catalog item` | `catalog` | `catalog` (infrastructure_bottleneck) |
| Order completes but no email | `notification` restart loops | `panic: nil pointer deref` | `notification` | `notification` (poison_pill_crash) |
| Frontend returns white screen | `frontend` 0 RPS downstream | `syntax error in bundle.js` | `frontend` | `frontend` (bad_release) |

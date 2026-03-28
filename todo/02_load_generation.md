# Task: Build Locust Load Generator + Custom Demo Control Panel

## Context & Objective
You are operating within the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/`). The project has 9 FastAPI microservices deployed under `v2/microservices/` on these ports:

| Service | Port | Downstream |
|---------|------|------------|
| `frontend-service` | 8001 | → auth-service:8002 |
| `auth-service` | 8002 | → catalog-service:8003 |
| `catalog-service` | 8003 | → inventory-service:8005 |
| `cart-service` | 8004 | → catalog-service:8003 |
| `inventory-service` | 8005 | *(leaf)* |
| `payment-service` | 8006 | → notification-service:8009 |
| `shipping-service` | 8007 | → inventory-service:8005 |
| `recommendation-service` | 8008 | → catalog-service:8003 |
| `notification-service` | 8009 | *(leaf)* |

Every service exposes:
- `GET /health` — returns `{"status": "ok"}`
- `GET /process` — calls downstream, returns chain result
- `GET /fault/crash` — calls `os._exit(1)` (kills the container)
- `GET /fault/timeout` — sleeps 7 seconds, returns
- `GET /fault/error` — returns HTTP 500

Your job is to build **two things**:
1. A **Locust load generator** that simulates realistic multi-path traffic across the service mesh.
2. A **custom HTML demo control panel** for orchestrating live hackathon demos.

**Do NOT** modify the microservices, observability stack, or dashboard. Only build the load generation and control panel.

---

## Output Directory

All files go under `/home/xd/Coding/colony_ps3/v2/loadgen/`. Create this directory.

---

## Part 1: Locust Load Generator

### File: `v2/loadgen/locustfile.py`

Write a Locust script with the following behavior:

#### Task Design
Define a single `MicroserviceUser(HttpUser)` class with multiple `@task` decorated methods. Each task must hit a **different entry point** in the service mesh to exercise multiple topology branches:

```python
@task(5)   # Highest weight — most common path
def full_chain_via_frontend(self):
    """frontend → auth → catalog → inventory"""
    self.client.get("/process", name="frontend-service /process")

@task(3)
def cart_flow(self):
    """cart → catalog → inventory"""
    # Must override base URL to hit cart-service:8004
    requests.get("http://cart-service:8004/process")

@task(2)
def payment_flow(self):
    """payment → notification"""
    requests.get("http://payment-service:8006/process")

@task(2)
def shipping_flow(self):
    """shipping → inventory"""
    requests.get("http://shipping-service:8007/process")

@task(1)
def recommendation_flow(self):
    """recommendation → catalog → inventory"""
    requests.get("http://recommendation-service:8008/process")
```

**Important implementation notes:**
- The `HttpUser` base host should be `http://frontend-service:8001` (the main entry point).
- For tasks that hit services other than the frontend, use `requests.get()` directly (not `self.client.get()`) since those are different hosts. BUT still wrap them so failures are properly reported to Locust stats.
- **Name every request** with `name="<service-name> /process"` so the Locust dashboard stats table shows per-service breakdown.
- Set `wait_time = between(0.5, 2)` for realistic spacing.

#### NO Automatic Chaos
Do **NOT** add any automatic chaos/fault injection tasks. Chaos is triggered manually from the control panel (Part 2). The Locust script only generates normal healthy traffic.

### File: `v2/loadgen/requirements.txt`
```
locust==2.24.0
requests==2.31.0
```

### File: `v2/loadgen/Dockerfile`
```dockerfile
FROM python:3.11-slim

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

EXPOSE 8089

CMD ["locust", "-f", "locustfile.py", "--host=http://frontend-service:8001", "--web-host=0.0.0.0"]
```

The default Locust web UI will be accessible at `http://localhost:8089` — leave this fully functional. Judges may want to see it.

---

## Part 2: Custom Demo Control Panel

### File: `v2/loadgen/control-panel.html`

Build a **single-file HTML page** (no build tools, no npm, no framework) that serves as a hackathon demo command center. Use inline CSS and JavaScript.

#### Design Requirements
- **Dark theme** (gray-950 background, similar to the project's Next.js dashboard aesthetic)
- **Premium, polished look** — this will be shown to hackathon judges. Use a modern sans-serif font (import Inter from Google Fonts), subtle gradients, and smooth transitions.
- **Responsive** — should look good on a single laptop screen

#### Layout (Top to Bottom)

**Section 1: Header**
- Title: "Colony PS3 — Demo Control Panel"
- Subtitle: "Real-Time AI Observability & Auto-Remediation System"
- A small live status indicator (green dot + "Locust Connected" / red dot + "Disconnected") that pings `http://localhost:8089/stats/requests` every 2 seconds to verify Locust is running.

**Section 2: Traffic Control**
Two inputs + one button + a countdown display:
- Input 1: `Number of Users` (default: 50)
- Input 2: `Delay (seconds)` (default: 5) — this gives the presenter time to switch to the telemetry dashboard
- Button: `🚀 Schedule Load`
- On click: Show a large, visible countdown timer (5... 4... 3... 2... 1...) that judges can see, then fire:
  ```
  POST http://localhost:8089/swarm
  Content-Type: application/x-www-form-urlencoded
  Body: user_count=<N>&spawn_rate=10&host=http://frontend-service:8001
  ```
- Also include a `🛑 Stop All Traffic` button that calls:
  ```
  GET http://localhost:8089/stop
  ```

**Section 3: Chaos Injection**
A grid of buttons (3 columns × 7 rows) for manually triggering faults on specific services. Only include non-frontend, non-leaf services that would create interesting cascading failures:

For each of these services: `auth-service`, `catalog-service`, `cart-service`, `payment-service`, `shipping-service`, `recommendation-service`, `notification-service`:
- 🔴 **Crash** button → `GET http://<service>:<port>/fault/crash`
- 🟡 **Timeout** button → `GET http://<service>:<port>/fault/timeout`
- ❌ **Error** button → `GET http://<service>:<port>/fault/error`

Each button should:
- Show a brief flash animation on click (green for sent, red on network error)
- Log the action to a small event log at the bottom of the panel
- Use `fetch()` with `mode: 'no-cors'` since we're hitting different ports

**IMPORTANT:** The chaos buttons must hit the services via `localhost:<port>` (not Docker hostnames) since this HTML page runs in the **browser**, not inside Docker. Map the ports:
- auth-service → `localhost:8002`
- catalog-service → `localhost:8003`
- cart-service → `localhost:8004`
- payment-service → `localhost:8006`
- shipping-service → `localhost:8007`
- recommendation-service → `localhost:8008`
- notification-service → `localhost:8009`

**Section 4: Event Log**
A scrolling terminal-style log at the bottom (dark background, monospace font) that records every action taken from this panel with timestamps:
```
[05:45:12] 🚀 Scheduled 50 users in 5 seconds
[05:45:17] ✅ Traffic started — 50 users spawning at 10/s
[05:45:32] 🔴 Crash injected → payment-service:8006
[05:45:44] 🛑 Traffic stopped
```

#### How to serve it
This is a static HTML file. The presenter simply opens it directly in their browser (`file:///path/to/control-panel.html`) or we can serve it via a tiny Python HTTP server. No build step needed.

---

## Final Checklist

- [ ] `v2/loadgen/locustfile.py` exists with multi-path traffic tasks weighted by topology importance
- [ ] Locust tasks use named requests so stats show per-service breakdown
- [ ] No automatic chaos injection in the Locust script
- [ ] `v2/loadgen/Dockerfile` exposes port 8089 and starts Locust web UI
- [ ] `v2/loadgen/control-panel.html` is a single self-contained HTML file
- [ ] Control panel has: traffic scheduler with countdown, chaos injection grid, event log
- [ ] Chaos buttons hit `localhost:<port>` (browser-side), not Docker hostnames
- [ ] Traffic control hits Locust API at `localhost:8089`
- [ ] Dark theme, polished aesthetic, Inter font loaded

---

## ⚠️ OUTPUT DIRECTORY — READ THIS

All files MUST be written under `/home/xd/Coding/colony_ps3/v2/loadgen/`. The complete file list:
```
/home/xd/Coding/colony_ps3/v2/loadgen/locustfile.py
/home/xd/Coding/colony_ps3/v2/loadgen/requirements.txt
/home/xd/Coding/colony_ps3/v2/loadgen/Dockerfile
/home/xd/Coding/colony_ps3/v2/loadgen/control-panel.html
```

---

## 🔍 Mandatory 2-Pass Self-Review

After generating all files, you MUST perform two review passes:

### Pass 1 — Structural Correctness
- Verify all service hostnames and ports in `locustfile.py` match the topology table
- Verify all `localhost:<port>` mappings in `control-panel.html` are correct
- Verify the Locust REST API endpoints used (`/swarm`, `/stop`, `/stats/requests`) are correct for Locust 2.x
- Verify the Dockerfile CMD starts Locust with `--web-host=0.0.0.0`

### Pass 2 — Demo Polish
- Open `control-panel.html` mentally and trace through the user flow: set users → set delay → click schedule → countdown appears → traffic starts
- Verify the countdown timer is large and visible (judges need to see it from a distance)
- Verify chaos buttons have the correct fault type in their URL path (`/fault/crash`, `/fault/timeout`, `/fault/error`)
- Verify the event log auto-scrolls to the latest entry

Document any fixes you make during each pass.

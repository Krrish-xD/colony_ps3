# Task: Build the v2 Dashboard — "The Digital Sentinel"

## Context & Objective
You are building the primary visual interface for the Colony PS3 AI Observability project. This is the **main thing hackathon judges see**. It must look premium, cyberpunk-inspired, and feel alive with real-time data.

The design follows a provided reference image with a dark sci-fi aesthetic: near-black backgrounds, cyan/teal accents, monospace fonts for headings, glowing effects on active nodes, and status-driven color coding.

**Stack:** Next.js 14 (App Router) + React + Tailwind CSS + react-force-graph-2d

**Port:** `3000` on the `colony-net` Docker network.

---

## Output Directory

All files in `/home/xd/Coding/colony_ps3/v2/dashboard/`. Create a new Next.js project here.

---

## Design Language

- **Background:** Near-black (`#0a0e17` or similar dark navy)
- **Cards:** Dark gray with subtle border (`#1a1f2e` bg, `#2a3040` border, slight rounded corners)
- **Primary accent:** Cyan/teal (`#00d4ff` / `#00e5c7`)
- **Critical/Error:** Red (`#ff3b5c`)
- **Warning:** Amber (`#ffaa00`)
- **Success/Healthy:** Green (`#00e676`)
- **Info/AI:** Purple (`#a855f7`)
- **Text:** White for headings, gray-400 for labels, monospace font (JetBrains Mono or Space Mono from Google Fonts) for headings and stats
- **Body font:** Inter or system sans-serif
- **UI Feel:** Glowing borders on active elements, subtle pulse animations on live indicators, scan-line or grid background overlay for sci-fi feel

---

## App Structure — 5 Bottom Tab Navigation

The app has a persistent bottom navigation bar with 5 tabs:

```
[ TERMINAL ] [ METRICS ] [ TOPOLOGY (default) ] [ TRACES ] [ AI RCA ]
```

The active tab has a cyan underline/glow. Each tab loads a different page view.

---

## Tab 1: TOPOLOGY (Default/Home Page) — Based on Reference Image

This is the main page. Layout (top to bottom):

### Header
- Logo icon + "THE DIGITAL SENTINEL" title (monospace, uppercase, cyan glow)
- User avatar / settings icon top-right

### Status Banner
- Large status badge: "OPERATIONAL" (green) or "ANOMALY DETECTED" (red pulsing)
- Cluster name subtitle: "CLUSTER: COLONY-PS3-V2"

### Stats Cards Row (3 cards, horizontal)
```
┌─────────────────┐ ┌─────────────────┐ ┌─────────────────┐
│ GLOBAL UPTIME   │ │ TOTAL INCIDENTS │ │ AVG RESOLUTION  │
│ 99.98% ▲ 0.02%  │ │ 12  7 High Pri  │ │ 3.6s  Stable    │
└─────────────────┘ └─────────────────┘ └─────────────────┘
```
- Uptime: calculated from service health checks
- Total incidents: count from `GET remediation:5001/incidents`
- Avg Resolution: average `total_pipeline_ms` from incidents — show in seconds

### Live Service Topology
- Force-directed graph using `react-force-graph-2d`
- **Node shapes:** Use different geometric shapes per service type (not just circles)
  - Frontend: hexagon
  - Auth/Catalog/Cart: triangle
  - Payment/Shipping: square
  - Inventory/Recommendation/Notification: circle
- **Node colors:** Green (healthy), Red pulsing (failing), Yellow (recovering), Cyan glow on selected
- **When an anomaly hits:** The failing node turns red + all upstream services in the blast radius glow orange
- Reset and zoom control buttons overlaid (bottom-right of graph area)

### Service Inventory
- Header: "SERVICE INVENTORY" with badge showing critical count (e.g., "1 CRITICAL" in red)
- Scrollable list of all 9 services:
  ```
  [colored dot] SERVICE_NAME
  LATENCY: XXms                           [status icon]
  ```
- Status dot colors: red = critical, yellow = degraded, green = healthy
- Pull data from: SSE events for real-time status + REST API for initial load

### Real-Time Event Stream
- Title: "REAL-TIME EVENT STREAM" with current UTC timestamp
- Scrolling log entries with severity badges:
  ```
  [CRIT]  15:41:08  Service AUTH_GATEWAY_V2 reached max retry limit on port 443. Blast radius expanding.
  [INFO]  15:40:41  Auto-scaler triggered for CLUSTER_WEST_16. +4 nodes deployed.
  [AI]    15:40:30  Predictive maintenance suggested for DATA_LAKE shard #56. Risk score: 0.84.
  ```
- Badge colors: CRIT=red, INFO=cyan, AI=purple, WARN=amber
- Auto-scroll to bottom on new events

---

## Tab 2: METRICS

Show live Prometheus metric charts. For now, use placeholder/mock data that looks realistic.

### Layout
- 4 chart panels in a 2x2 grid:
  1. **Request Rate (RPS)** — line chart, per-service colored lines
  2. **P95 Latency** — line chart with threshold line at 2000ms
  3. **Error Rate (5xx)** — area chart, stacked by service
  4. **LSTM Prediction vs Actual** — dual-line chart showing predicted (dashed cyan) vs actual (solid white) latency

### Mock Data
Generate fake time-series data (last 60 data points, 1 per second) for each chart. Make it look realistic with slight noise and occasional spikes.

Use a lightweight charting library: `recharts` or `chart.js` with react-chartjs-2.

---

## Tab 3: TRACES

Show recent distributed traces. For now, use placeholder/mock data.

### Layout
- **Recent Traces list** — table with columns: Trace ID (truncated), Service, Duration, Status, Timestamp
- **Trace Detail** — when a trace is clicked, show a waterfall/flame chart of spans
  - Each span is a horizontal bar showing service name, duration, and status
  - Nested spans indented to show call hierarchy

### Mock Data
Generate 5-10 fake traces with realistic span hierarchies following the service topology.

---

## Tab 4: TERMINAL

A full-screen terminal emulator view.

### Layout
- Dark terminal background with green/cyan monospace text
- Shows ALL raw events from the SSE stream (unfiltered)
- Each line prefixed with timestamp and severity
- Manual scroll, auto-scroll toggle button
- Filter input at top to grep events by keyword

---

## Tab 5: AI RCA

The intelligence/ML results page.

### Layout
- **Latest Incident Card** — large card showing the most recent RCA result:
  - Service name, root cause classification, confidence bar (visual progress bar, colored by tier)
  - Evidence chain timeline (vertical timeline with metric/log/trace icons)
  - Timing breakdown bar: `Detection → RCA → Restart → Verified`
  - Blast radius mini-graph showing affected services
- **Incident History Table** — scrollable table of past incidents
  - Columns: #, Time, Service, Root Cause, Confidence, Action, Health ✓, Pipeline Time
- **Fingerprint Similarity** — card showing "Similar to incident #X (96% match), fix success: 4/4"

### Mock Data
Generate 5-10 fake incident records with realistic evidence chains for initial display.

---

## SSE Integration

The dashboard connects to its own backend API route:

### `GET /api/events` — SSE endpoint
- Proxies events from the remediation engine
- Also accepts POST from remediation engine to broadcast to all connected SSE clients
- Format: each event is a JSON object with `type` field ("remediation", "alert", "health", "ping")

### `POST /api/events` — receives events from remediation engine
- Stores in an in-memory buffer
- Broadcasts to all connected SSE clients

### `GET /api/topology` — returns the service topology graph
- Returns the node/edge data for the force graph
- Query Jaeger API for real topology, with hardcoded fallback

### `GET /api/proxy/incidents` — proxies to remediation:5001/incidents
### `GET /api/proxy/prometheus` — proxies PromQL queries to prometheus:9090

---

## Docker Setup

### `Dockerfile`
```dockerfile
FROM node:20-alpine
WORKDIR /app
COPY package*.json ./
RUN npm ci
COPY . .
RUN npm run build
EXPOSE 3000
CMD ["npm", "start"]
```

### Network
Joins `colony-net` (external Docker network).

---

## ⚠️ OUTPUT DIRECTORY

All code under `/home/xd/Coding/colony_ps3/v2/dashboard/`.

---

## 🔍 Mandatory 2-Pass Self-Review

### Pass 1 — Structural
- All 5 tab routes exist and render
- Bottom navigation highlights the active tab with cyan
- SSE connection established on page load
- Force graph renders with 9 nodes matching the service topology
- All mock data looks realistic (no "lorem ipsum" or obviously fake numbers)

### Pass 2 — Visual Polish
- Background is near-black, not gray
- Monospace font loaded (Google Fonts: Space Mono or JetBrains Mono)
- Stats cards have subtle borders and rounded corners
- Service inventory dots match status colors (red/yellow/green)
- Event stream auto-scrolls and shows severity badges with correct colors
- Bottom nav tabs have cyan active indicator

Document any fixes during each pass.

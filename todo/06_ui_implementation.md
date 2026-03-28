# Task: Build the v2 UI Framework (Dashboard & Control Panel)

## Context & Objective
You are building the two primary user interfaces for the Colony PS3 AI Observability project. These interfaces must look premium, dark, and cyberpunk-inspired (matching the "Digital Sentinel" aesthetic).

We are taking inspiration from the `v1/dockprom` (which used Grafana) and `v1/locust` setups, but replacing them with custom, high-performance web apps built with Next.js and typical modern React tooling.

**Tech Stack:**
- Framework: Next.js 14 (App Router)
- Styling: Tailwind CSS
- Data Visualization: `recharts` (for metrics), `react-force-graph-2d` (for topology)
- Icons: `lucide-react`

**CRITICAL PREREQUISITE:**
Before you write any code, you MUST view the 5 reference images located in `/home/xd/Coding/colony_ps3/v2/dashboard ui/`. These images provide the exact layout, color palette, and visual aesthetic you are required to implement. Do not proceed without studying them carefully.

---

## App 1: The Command Center (Port 4000)
**Location:** `/home/xd/Coding/colony_ps3/v2/loadgen/ui/` (Create a new Next.js project here)

This app is the presenter's control panel. It interacts with the Locust load generator and the microservices' fault endpoints.

### Layout Requirements (based on `command center.png`):
- **Background & Theme:** Very dark navy (`#0B0E14`), monospace fonts for data (`JetBrains Mono` or similar), cyan accents (`#00E5FF`).
- **Header:** "THE DIGITAL SENTINEL" with an operator badge.
- **Traffic Control Section:**
  - Inputs for "SPAWN X USERS" and "SPAWN INTERVAL".
  - Large digital countdown timer ("SESSION COUNTDOWN").
  - Cyan "EXECUTE" button and Red "STOP ALL" button.
- **Live Stats Column:**
  - Real-time RPS (e.g., 12.4k).
  - Error % (e.g., 0.02%).
  - Avg Latency (e.g., 42ms).
  - Aggregated Latency Distribution (bar chart for P95/P99).
- **Chaos Grid:**
  - List of services (e.g., `AUTH_SRV_01`, `PYMT_GATEWAY`).
  - Status indicator dot (Green = Stable, Yellow = Degraded).
  - Action buttons: "KILL" (dark), "RECOVER" (red).
- **System Action Log:**
  - Scrolling terminal window at the bottom.
  - Bracketed timestamps `[14:22:01]`, severity labels (`AI_INSIGHT:`, `COMMAND:`, `CHAOS:`), and message text.

### Functionality:
- Implement the UI visually first using mock data.
- The "EXECUTE" and "STOP ALL" buttons should make dummy API calls (we will wire them up to Locust later).

---

## App 2: The Main Dashboard (Port 3000)
**Location:** `/home/xd/Coding/colony_ps3/v2/dashboard/` (Create a new Next.js project here)

This is the primary visualizations platform, replacing Grafana from v1. It features a bottom navigation bar to switch between 5 views.

### Common Layout Elements:
- Same dark sci-fi aesthetic as the Command Center.
- **Bottom Navigation Bar:** 5 tabs (`[ TERMINAL ]`, `[ METRICS ]`, `[ TOPOLOGY ]` (default), `[ TRACES ]`, `[ AI RCA ]`). Active tab glows cyan.

### View 1: Topology (`system overview.png`) - Default
- **Header:** "OPERATIONAL_NODE", Cluster Name.
- **Top Stats Row:** GLOBAL UPTIME (99.98%), TOTAL INCIDENTS (12), AVG RESOLUTION (14m 22s).
- **Live Service Topology:**
  - Use `react-force-graph-2d`.
  - Floating geometric nodes with cyan borders. Failing nodes pulse red.
- **Service Inventory (Left/Right Sidebar):**
  - List of services. Left border color indicates status (cyan = healthy, red = critical, muted pink = warning).
  - Show latency under the service name.
- **Real-Time Event Stream (Bottom):**
  - Scrolling log of events with bracketed severity tags `[CRIT]`, `[INFO]`, `[AI]`.

### View 2: Metrics (`deep metrics.png`)
- **Header:** "SYSTEM LATENCY & THROUGHPUT".
- **Time Selector:** Dropdown for service, buttons for `1H`, `6H`, `24H`, `7D`.
- **Charts (using Recharts):**
  1. **Latency Percentiles:** Smooth multi-line chart (P50, P95, P99).
  2. **Traffic Volume vs Errors:** Overlapping area chart (Cyan for requests, Red for errors).
  3. **LSTM Traffic Forecast:** Line chart transitioning into a dotted line for predictions.
- **Cluster Service Metadata:** Table showing Service, Uptime, CPU Limit, Memory.
- **AI RCA Intel Panel:** Small card showing AI insights (e.g., "Anomaly detected...").

### View 3: Traces (`log tracer.png`)
- **Header:** Search bar with query syntax (e.g., `{service='auth-api'}`).
- **Log Stream:**
  - Color-coded left borders matching severity (Red=ERR, Yellow=WRN, Cyan=INF).
  - Timestamp, Tag, and Message text.
- **Trace Explorer (Modal/Overlay):**
  - Waterfall chart showing span durations (e.g., API Gateway -> Auth Service -> DB Select).
- **Metadata Details:** JSON code block visualization below the trace.
- **Anomalies Detected (AI):** Callout box explaining the root cause found in the trace.

### Other Views:
- **Terminal:** Full-screen version of the system action log.
- **AI RCA (`rca intelligence.png`):** Focus on the incident history and ML confidence scores.

---

## Technical Constraints & Setup
1. **Ports:**
   - Next.js Dashboard: `3000`
   - Next.js Command Center: `4000`
2. **Dockerization:**
   - Both apps need a standard Next.js `Dockerfile`.
   - They will join the `colony-net` external Docker network.
3. **Data Strategy:**
   - Build out the entire UI structure and styling using **Hardcoded/Mock Data** first.
   - The visuals must match the provided reference images as closely as possible.

## ⚠️ OUTPUT DIRECTORY
Create the Next.js apps in:
- `/home/xd/Coding/colony_ps3/v2/loadgen/ui/`
- `/home/xd/Coding/colony_ps3/v2/dashboard/`

## 🔍 Mandatory Self-Review
- Ensure both apps use the dark `#0B0E14` aesthetic with `#00E5FF` (cyan) and `#FF3B5C` (red) accents.
- Verify the 5-tab bottom navigation exists in the Dashboard app.
- Verify `react-force-graph-2d` and `recharts` are included in the package.json.
- Run `npm run build` locally in both folders to ensure they compile without errors before finishing.

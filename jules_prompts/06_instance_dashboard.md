# 🎯 Global Jules Context

## The Problem Statement
You are participating in a 30-hour Hackathon. The objective is to build a real-time AI observability system that ingests live logs and metrics from a distributed application, performs root cause analysis, and triggers automated remediation end-to-end under 15 seconds. 

## The Target System Architecture
We are building a 4-tier microservice architecture (Frontend, Auth, Cart, Payment) instrumented with OpenTelemetry.
- Locust generates background traffic and triggers deliberate chaos.
- Telemetry flows to an OTel Collector, which routes to Prometheus, Loki, and Jaeger.
- Prometheus Alertmanager evaluates PromQL rules (e.g., `rate(http_5xx) > 5%`).
- When tripped, a push webhook hits our Python RCA Engine. The engine waits 3 seconds (micro-buffer for ingestion latency), safely queries Loki for logs on the exact failing service, maps the error to a known issue, and sends an action back to our Auto-Remediation Engine.
- The Remediation Engine restarts the container via the Docker socket (checking a 30s cooldown cache to prevent infinite loops).
- A Next.js Server-Sent Events (SSE) Dashboard pulses the system nodes in real time to visualize the failure and recovery.

## ⚠️ Global Jules Instructions
1. **Demo Constraint:** Write ONLY what is needed for a 3-minute demo. Omit production auth, TLS, or persistent DB volumes. Optimize everything for sub-100ms execution times to meet the strict 15-second system latency budget.
2. **Determinism:** Do not use probabilistic ML models. Use strict IF/ELSE rule-matching against explicit JSON payload contracts.
3. **Boundary Constraint:** Work EXCLUSIVELY in your assigned directory. Do not drift into modifying other folders. The rest of the team (other Jules instances) is handling the other components.
4. **Environment Constraints:** No Kubernetes. Everything runs on Docker Compose.
5. **Required Reading (CRITICAL):** Before writing any code, you MUST use your tools to read the master architecture document located at `ag_research/final_system_guide.md` in its entirety to understand the system nuances and technical trade-offs.

---

# 🚀 Your Specific Assignment: Instance 6 (React Dashboard)

**You only work in the `/dashboard` folder.**

You are building the UI layer that visualizes the magic to the judges. A laggy or failing UI means a failed demo.
Your task is to build a clean **Next.js / React** application heavily styled with **Tailwind CSS**. 

## 🏗️ Execution Specifications:
1. **No Backend Polling Constraint**: You must implement Server-Sent Events (SSE) logic on the backend route (`/api/events`) to consume a live stream of RCA operational events pushed by the external Remediation Engine. 
2. **Topology Discovery**: On page mount, perform an HTTP GET to Jaeger's `/api/dependencies` endpoint. Dynamically draw a forced-directed node graph representing the layout. Provide an immediate clean static fallback array (`frontend-service`, `auth-service`, `cart-service`, `payment-service`) if the Jaeger API fails during the hackathon. Ensure the UI has an "Activate Demo Mode" button to mock SSE events flawlessly in case the backend crashes during presentation.
3. **UI Pulse Triggers**: When an SSE event fires stating a container is failing, immediately pulse the corresponding graph node RED via Tailwind classes (`animate-pulse bg-red-500`). Append a log entry into an "Event Stream" terminal UI visualizing the RCA action. Once the `restart` payload resolves, pulse the node GREEN.
4. **Output Expectations**: Include a valid `Dockerfile` optimized for Next.js standalone execution. Output a clean web-ready directory structure.

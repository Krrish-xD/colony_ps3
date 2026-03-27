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

# 🚀 Your Specific Assignment: Instance 8 (Integration & Deployment)

**You only work in the `/deploy` folder.**

You are the system orchestrator uniting 8 different repositories of work into a cohesive execution environment. 
Your task is to synthesize the compiled artifacts of all previous Jules instances into a single master `docker-compose.yml` file.

## 🏗️ Execution Specifications:
1. **Service Registration**: You must accurately declare all 4 microservices from dynamically mapped `./services/<service-name>` paths, the components from `/observability`, `/intelligence`, `/remediation`, and `/dashboard`. Use `depends_on` meticulously so observability layers boot before intelligence, and intelligence before services.
2. **Docker Network Discovery**: Enforce a rigid custom bridge network so services can resolve HTTP hostnames identically to the code configurations (e.g., Prometheus reaching out to `http://intelligence:8000/alert` successfully).
3. **Docker Socket Mount (CRITICAL SECURITY SHORTCUT)**: You must append the `volumes:` block specifically for the `/remediation` container to cleanly mount `- /var/run/docker.sock:/var/run/docker.sock:ro`. Without this explicit volume mount, the Auto-Remediation Python script will permanently hang when firing commands, breaking our 15s latency budget.

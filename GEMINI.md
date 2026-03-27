# Colony PS3 Project Context

## Current State
- **Phase**: System Design & Architecture Initialization (Completed). Ready to begin Phase 1 (Infrastructure Implementation).
- **Goal**: Conceptualize an end-to-end, sub-15-second anomaly detection, RCA, and auto-remediation pipeline.

## System Architecture (Final)
The design features a lightweight, 4-tier microservice architecture instrumented with OpenTelemetry.
Telemetry is piped to Prometheus, Loki, and Jaeger.
- **Detection**: PromQL rules on Prometheus Alertmanager (push-based triggers), ensuring guaranteed anomaly hits during a live demo.
- **RCA / Remediation**: A custom Python engine that receives the target node from Alertmanager, waits precisely 3 seconds (to bypass ingestion latency), queries Loki for exact errors, and remediates via the Docker socket (with a 30s restart cooldown cache to prevent loops).
- **Dashboard**: A custom Next.js/React + SSE (Server-Sent Events) frontend dynamically mapping the live topology (via Jaeger) and showing real-time event logs of the RCA logic.

## Directory Structure
- `ag_research/`: Contains the complete, final architectural synthesis and design history. 
  - `ag_research/final_system_guide.md`: **The authoritative Master System Documentation.** All final design, latency strategies, and component breakdowns live here.
- `README.md`: Main entry point summarizing the hackathon project problem statement, architecture flow, and multi-phase implementation plan.

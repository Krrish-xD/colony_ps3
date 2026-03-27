# Colony PS3 Project Context

## Current State
- **Phase**: v1 System Completed & Archived (`/v1`). Commencing `v2` Architecture & Planning Phase.
- **Goal**: Expand the autonomous observability & remediation pipeline beyond the hackathon-constrained bounds of `v1` into a robust, state-of-the-art `v2` implementation.

## System Architecture (v1 Review)
The v1 design successfully achieved a lightweight, 4-tier microservice architecture instrumented with OpenTelemetry.
- **Detection**: PromQL rules on Prometheus Alertmanager (push-based triggers), ensuring guaranteed anomaly hits during a live demo.
- **RCA / Remediation**: A custom Python engine that receives the target node from Alertmanager, waits precisely 3 seconds, queries Loki for exact errors, and remediates via the Docker socket (with a 30s restart cooldown cache).
- **Dashboard**: A custom Next.js/React + SSE frontend dynamically mapping the live topology and showing real-time event logs of the RCA logic.

## Directory Structure
- `v1/`: Complete archive of the functional Hackathon MVP.
- `README.md`: Main entry point summarizing the hackathon project problem statement, architecture flow.
- (New) `v2/`: To be bootstrapped.

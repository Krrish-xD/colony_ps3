# Colony PS3 Project Context

## Current State
- **Phase**: v1 & v2 Architecture Completed. Commencing `v3` Planning Phase.
- **Goal**: Build the final, production-grade v3 iteration. The core focus is expanding microservice complexity so that each service can emit multiple, distinct, overlapping error types. This will force the ML RCA routing engine to perform true diagnostic classification rather than just node-level identification.

## System Architecture (v1 & v2 Review)
The previous iterations successfully shipped:
- A 9-tier FastAPI microservice mesh on Docker Compose.
- **Detection**: PromQL & Alertmanager 1s evaluation loops.
- **RCA / Remediation**: A Python intelligence engine using an LSTM for metric forecasting and a PyTorch Fusion Classifier (Logs via MiniLM, Metrics, Traces) to trigger confidence-gated remediations via the Docker Socket.
- **Dashboard**: A React Next.js sci-fi dashboard visualizing live distributed topology and SSE events.

## Directory Structure
- `v1/`: Hackathon MVP archive.
- `v2/`: Previous 9-tier iteration.
- `README.md`: Main entry point.
- (New) `v3/`: Under active planning.

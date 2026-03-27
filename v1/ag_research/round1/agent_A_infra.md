# Round 1

## Idea
Use Docker Compose to deploy a lightweight multi-service app alongside a k6 load generator, minimizing networking overhead and ensuring rapid deployment for the hackathon.

## Approach
- Deploy 3-4 simple microservices (e.g., frontend, auth, payment, database) defined in a single `docker-compose.yml`.
- Deploy K6 (using `grafana/k6` image) on the same Docker network to continuously generate synthesized HTTP traffic.
- Expose application ports (e.g., 8080) and pre-instrument them for Prometheus metrics.

## Assumptions
- The entire system (microservices, observability stack, ML, and load generator) can run on a single host machine comfortably without resource starvation.
- Microservices are stateless, and traffic is purely HTTP-based.

## Risks
- The k6 load generator running on the same host might consume too much CPU, causing artificial latency spikes in the microservices that aren't representative of true application faults.

## Open Questions
- Do we need to simulate failure explicitly via chaos engineering scripts, or should we rely on K6 over-saturating the services?

## Evidence / References
- Search results confirmed that a single `docker-compose.yml` orchestrating K6 with microservices (SUT) and sending metrics to Prometheus is a highly common, robust pattern for latency testing.

## Input Contract
- Simulated traffic from Load Generator.
- Remediation commands (Docker API calls) from Agent D.

## Output Contract
- Exposed standardized metrics endpoints.
- Raw logs streamed to stdout.
- Raw traces emitted via OTLP.

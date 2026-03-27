## Pass 1 Review

- **Issues Found**:
  1. Promtail's `refresh_interval` for Docker SD is 5s, which might cause a tiny delay in discovering new containers (e.g., after remediation).
  2. The Loki `tsdb` configuration might be slightly heavy for a 3-minute hackathon demo, although it's the new default.
  3. The Jaeger configuration includes Prometheus metrics storage environment variables, but a simpler all-in-memory setup without dependencies on Prometheus for Jaeger metrics might be faster to start and more robust for a 3-minute demo.
  4. Port `14250` was mapped for Jaeger but Jaeger now supports OTLP natively via 4317 with `COLLECTOR_OTLP_ENABLED=true`. The extra port `14250` is unnecessary and adds clutter.
- **Why they are problems**:
  1. A 5-second interval can delay log capture for newly restarted containers, eating into our strict <15s end-to-end budget if another chaos event triggers immediately.
  2. We want to avoid any disk/compactor overhead if we can.
  3. Depending on Prometheus for Jaeger's internal metrics isn't required and adds an unnecessary startup dependency.
  4. Unnecessary ports can cause conflicts or confusion.
- **Fixes to apply**:
  1. Reduce Promtail `refresh_interval` to `1s`.
  2. Simplify Jaeger environment variables.
  3. Keep Loki as lightweight as possible. I'll stick to simple in-memory TSDB or BoltDB shipper without complex compactor settings, or just ensure the settings prioritize memory.

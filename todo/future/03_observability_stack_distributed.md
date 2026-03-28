# Task: Build the v2 Observability Stack

## Context & Objective
You are operating within the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/`). This stack powers a sub-5-second anomaly detection and auto-remediation pipeline running across a **distributed multi-machine setup**:

- **M5 (macOS, 16GB)** — runs the 9 microservices + Locust (this machine)
- **i5-11th (Windows/WSL2, 16GB)** — runs the observability stack (what you are building now)
- **i5-12H (Linux, 16GB, RTX 3050)** — runs the ML RCA engine
- **M3 (macOS, 8GB)** — runs the Next.js dashboard

Your job is to build **the complete observability stack** that runs on the `i5-11th (Windows/WSL2)` machine. This is a `docker-compose.yml` + all supporting config files.

**Do NOT** touch the microservices, the ML engine, the dashboard, or the load generator. Only build the observability layer.

---

## Reference Material

A working v1 implementation lives at:
- `/home/xd/Coding/colony_ps3/v1/observability/` — all config files (study these carefully)
- `/home/xd/Coding/colony_ps3/v1/deploy/docker-compose.yml` — the v1 compose file

Your v2 configs must carry over the v1 tuning (2s scrape, 100ms Promtail flush, aggressive Loki ingestion) and improve on it as detailed below.

---

## Output Directory

All files MUST be written to `/home/xd/Coding/colony_ps3/v2/observability/`. Create this directory.

Complete file list:
```
/home/xd/Coding/colony_ps3/v2/observability/docker-compose.yml
/home/xd/Coding/colony_ps3/v2/observability/otel-collector-config.yaml
/home/xd/Coding/colony_ps3/v2/observability/prometheus.yml
/home/xd/Coding/colony_ps3/v2/observability/rules.yml
/home/xd/Coding/colony_ps3/v2/observability/alertmanager.yml
/home/xd/Coding/colony_ps3/v2/observability/loki-config.yaml
/home/xd/Coding/colony_ps3/v2/observability/promtail-config.yaml
/home/xd/Coding/colony_ps3/v2/observability/grafana/provisioning/datasources/datasources.yaml
/home/xd/Coding/colony_ps3/v2/observability/grafana/provisioning/dashboards/dashboards.yaml
/home/xd/Coding/colony_ps3/v2/observability/grafana/dashboards/services-overview.json
```

---

## Architecture Overview

```
[M5 — 9 Microservices]
    ├── OTLP HTTP (traces+metrics) → OTel Collector:4318 (this machine)
    └── stdout JSON logs → Promtail (this machine, via TCP/Docker log driver or log file mount)

[OTel Collector] →  Prometheus (metrics via scrape of Collector:8889)
                →  Jaeger (traces via OTLP gRPC)
                →  Loki (logs via OTLP log pipeline)

[Prometheus] → Alertmanager → webhook → RCA Engine on i5-12H:5000

[Grafana] ← queries Prometheus + Loki + Jaeger

Exposed ports on this machine (i5-11th):
  OTel Collector:   0.0.0.0:4317, 0.0.0.0:4318
  Prometheus:       0.0.0.0:9090
  Alertmanager:     0.0.0.0:9093
  Loki:             0.0.0.0:3100
  Jaeger UI:        0.0.0.0:16686
  Grafana:          0.0.0.0:3001   ← use 3001 to avoid clash with dashboard on 3000
  Promtail:         (internal only)
```

---

## File 1: `docker-compose.yml`

Build a single Docker Compose file that starts all 7 services. Key requirements:

### Network
- Single bridge network named `observability-net`
- Bind all listening ports to `0.0.0.0` so the other machines on LAN can reach them

### Services

**`otel-collector`**
- Image: `otel/opentelemetry-collector-contrib:0.97.0` (use `contrib` variant — it has the Loki exporter)
- Config: `./otel-collector-config.yaml`
- Ports: `4317:4317` (gRPC), `4318:4318` (HTTP), `8889:8889` (Prometheus metrics scrape endpoint)
- Must start after `loki` and `jaeger`

**`prometheus`**
- Image: `prom/prometheus:v2.51.0`
- Command flags: `--config.file`, `--web.enable-lifecycle`, `--storage.tsdb.retention.time=2h`, `--storage.tsdb.retention.size=500MB`
- Config: `./prometheus.yml` and `./rules.yml` mounted
- Port: `9090:9090`

**`alertmanager`**
- Image: `prom/alertmanager:v0.27.0`
- Config: `./alertmanager.yml`
- Port: `9093:9093`

**`loki`**
- Image: `grafana/loki:2.9.8`
- Config: `./loki-config.yaml`
- Port: `3100:3100`

**`jaeger`**
- Image: `jaegertracing/all-in-one:1.56`
- Environment: `COLLECTOR_OTLP_ENABLED=true`, `SPAN_STORAGE_TYPE=memory`, `MEMORY_MAX_TRACES=5000`
- Ports: `16686:16686` (UI), `4317` (internal gRPC — internal only, no host binding needed since OTel Collector is on same compose network)

**`promtail`**
- Image: `grafana/promtail:2.9.8`
- Config: `./promtail-config.yaml`
- Volumes: `/var/log` mount + Docker socket mount (`/var/run/docker.sock:/var/run/docker.sock:ro`)
- No external ports needed

**`grafana`**
- Image: `grafana/grafana:10.4.0`
- Port: `3001:3000`
- Environment:
  - `GF_SECURITY_ADMIN_PASSWORD=colony123`
  - `GF_USERS_ALLOW_SIGN_UP=false`
  - `GF_AUTH_ANONYMOUS_ENABLED=true`
  - `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`
- Volumes: mount `./grafana/provisioning` → `/etc/grafana/provisioning` and `./grafana/dashboards` → `/var/lib/grafana/dashboards`

---

## File 2: `otel-collector-config.yaml`

Carry over the v1 config with improvements:

**Receivers:**
- `otlp` with both `grpc` (0.0.0.0:4317) and `http` (0.0.0.0:4318)

**Processors:**
- `batch`: `timeout: 200ms`, `send_batch_size: 100` (keep v1 values — already tuned)
- `resource`: Carry the v1 label mappings exactly:
  ```yaml
  - key: service
    from_attribute: service.name
    action: insert
  - key: app
    from_attribute: service.name
    action: insert
  ```

**Exporters:**
- `prometheus`: endpoint `0.0.0.0:8889`, `resource_to_telemetry_conversion: enabled: true`
- `otlp/jaeger`: endpoint `jaeger:4317`, `tls: insecure: true`
- `loki`: endpoint `http://loki:3100/loki/api/v1/push`, with labels promoting `app` and `service` attributes

**Pipelines:**
```yaml
traces:   receivers: [otlp] → processors: [resource, batch] → exporters: [otlp/jaeger]
metrics:  receivers: [otlp] → processors: [resource, batch] → exporters: [prometheus]
logs:     receivers: [otlp] → processors: [resource, batch] → exporters: [loki]
```

---

## File 3: `prometheus.yml`

```yaml
global:
  scrape_interval: 1s        # ← v2 upgrade: drop from 2s to 1s for faster detection
  evaluation_interval: 1s    # ← v2 upgrade: evaluate rules every 1s

alerting:
  alertmanagers:
    - static_configs:
        - targets: ['alertmanager:9093']

rule_files:
  - '/etc/prometheus/rules.yml'

scrape_configs:
  - job_name: 'otel-collector'
    honor_labels: true
    static_configs:
      - targets: ['otel-collector:8889']
    metric_relabel_configs:
      # CRITICAL: Map job label → service label so RCA engine receives {"service": "payment-service"}
      - source_labels: [job]
        target_label: service
        action: replace
```

---

## File 4: `rules.yml`

Define PromQL alert rules for all 9 services. Key improvements from v1:

- **No `for:` clause on any rule** — instant triggering, no waiting period. This is intentional for sub-5s demo budget.
- Cover both error rate AND latency for thorough detection
- Add a **CrashLoop / Service Down** rule for when `os._exit(1)` is fired

```yaml
groups:
  - name: "v2-anomaly-detection"
    rules:
      - alert: HighErrorRate
        expr: rate(http_requests_total{http_status_code=~"5.."}[30s]) > 0.1
        labels:
          severity: critical
          metric: http_requests_total
        annotations:
          description: "{{ $labels.service }} is returning >10% 5xx errors over last 30s."

      - alert: LatencySpike
        expr: histogram_quantile(0.95, rate(http_server_duration_milliseconds_bucket[30s])) > 2000
        labels:
          severity: critical
          metric: http_server_duration_milliseconds
        annotations:
          description: "{{ $labels.service }} P95 latency exceeded 2000ms over last 30s."

      - alert: ServiceDown
        expr: up{job="otel-collector"} == 0
        labels:
          severity: critical
          metric: up
        annotations:
          description: "OTel collector lost contact with scrape target — a service may have crashed."
```

> **Note on metric names**: v2 services use OTel SDK auto-instrumentation via `FastAPIInstrumentor`. The actual metric names emitted are `http_server_duration_milliseconds` and `http_server_active_requests`. Adjust these if the actual metrics seen in Prometheus differ — check `http://localhost:9090/api/v1/label/__name__/values` after first startup to verify exact names.

---

## File 5: `alertmanager.yml`

```yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 0s        # ← v2 upgrade: was 1s, now 0s for instant dispatch
  group_interval: 10s
  repeat_interval: 2m
  receiver: 'rca-engine-webhook'

receivers:
  - name: 'rca-engine-webhook'
    webhook_configs:
      - url: 'http://<RCA_ENGINE_HOST>:5000/alert'
        # NOTE: Replace <RCA_ENGINE_HOST> with the LAN IP of the i5-12H machine
        # The RCA engine runs on port 5000 and expects Alertmanager's standard webhook payload
        send_resolved: true
        http_config:
          timeout: 3s
```

**IMPORTANT**: Leave `<RCA_ENGINE_HOST>` as a placeholder. The actual LAN IP of the i5-12H will be filled in during deployment. Mark this clearly in a comment.

---

## File 6: `loki-config.yaml`

Carry over the v1 config exactly but add memory caps:

```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn   # ← reduce log noise in production

common:
  path_prefix: /tmp/loki
  storage:
    filesystem:
      chunks_directory: /tmp/loki/chunks
      rules_directory: /tmp/loki/rules
  replication_factor: 1
  ring:
    kvstore:
      store: inmemory

schema_config:
  configs:
    - from: 2020-10-24
      store: tsdb
      object_store: filesystem
      schema: v13
      index:
        prefix: index_
        period: 24h

limits_config:
  ingestion_rate_mb: 50
  ingestion_burst_size_mb: 100
  max_entries_limit_per_query: 10000
  reject_old_samples: true
  reject_old_samples_max_age: 2h   # ← cap at 2h for hackathon demo
  per_stream_rate_limit: 50MB
  per_stream_rate_limit_burst: 100MB
  retention_period: 2h

ingester:
  chunk_idle_period: 100ms     # ← CRITICAL: flush chunks every 100ms for low query latency
  chunk_block_size: 102400
  chunk_retain_period: 30s
  max_transfer_retries: 0
  lifecycler:
    ring:
      kvstore:
        store: inmemory
      replication_factor: 1
    final_sleep: 0s
```

---

## File 7: `promtail-config.yaml`

Carry over the v1 config exactly. Key settings to preserve:
- `batchwait: 100ms` — flush to Loki every 100ms (critical for sub-5s RCA)
- `batchsize: 102400` — 100KB batch cap
- Docker service discovery via `docker_sd_configs`
- Relabel rules to extract `app` and `service` labels from Docker Compose service name
- JSON pipeline stage to parse our structured log JSON

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push
    batchwait: 100ms
    batchsize: 102400

scrape_configs:
  - job_name: docker
    docker_sd_configs:
      - host: unix:///var/run/docker.sock
        refresh_interval: 1s
    relabel_configs:
      - source_labels: ['__meta_docker_container_name']
        regex: '/(.*)'
        target_label: 'container'
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'app'
      - source_labels: ['__meta_docker_container_label_com_docker_compose_service']
        target_label: 'service'
    pipeline_stages:
      - docker: {}
      - match:
          selector: '{app=~".+"}'
          stages:
            - json:
                expressions:
                  level: level
                  trace_id: trace_id
                  error_type: error_type
            - labels:
                level:
                trace_id:
                error_type:
```

> **Note**: The v2 services log `trace_id` and `error_type` — extract these as Loki labels so the RCA engine can filter by them directly in LogQL.

---

## File 8: `grafana/provisioning/datasources/datasources.yaml`

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: false

  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
    editable: false

  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
    editable: false
```

---

## File 9: `grafana/provisioning/dashboards/dashboards.yaml`

```yaml
apiVersion: 1

providers:
  - name: 'Colony PS3'
    orgId: 1
    folder: 'Colony PS3'
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    options:
      path: /var/lib/grafana/dashboards
```

---

## File 10: `grafana/dashboards/services-overview.json`

Build a pre-configured Grafana dashboard JSON with the following panels. Use Grafana's JSON model format (version 36+):

**Panel 1: Request Rate per Service** (type: `timeseries`)
- PromQL: `rate(http_requests_total[30s])` grouped by `service`
- Title: "Request Rate (RPS) per Service"

**Panel 2: P95 Latency per Service** (type: `timeseries`)
- PromQL: `histogram_quantile(0.95, rate(http_server_duration_milliseconds_bucket[30s]))` by `service`
- Unit: milliseconds
- Title: "P95 Latency per Service"

**Panel 3: Error Rate per Service** (type: `timeseries`)
- PromQL: `rate(http_requests_total{http_status_code=~"5.."}[30s])` by `service`
- Title: "5xx Error Rate per Service"

**Panel 4: Active Alerts** (type: `alertlist`)
- Shows firing alerts from Alertmanager
- Title: "Active Anomaly Alerts"

**Panel 5: Live Log Stream** (type: `logs`)
- LogQL: `{app=~".+", level="error"}`
- Title: "Live Error Logs"

> Generate a valid Grafana JSON model for these 5 panels. Use a 2-column, 3-row grid layout. Dark theme. The dashboard `uid` should be `colony-ps3-overview` and title should be `Colony PS3 — Service Overview`.

---

## ⚠️ Critical Notes

1. **`<RCA_ENGINE_HOST>` in `alertmanager.yml`**: Leave as a literal placeholder with a clear comment. Do NOT hardcode a LAN IP.

2. **Metric name verification**: After startup, the actual OTel metric names from `FastAPIInstrumentor` may differ slightly from what's in `rules.yml`. The PromQL in `rules.yml` should be considered "best effort" — a comment must note this and give the command to verify actual metric names:
   ```bash
   curl http://localhost:9090/api/v1/label/__name__/values | python3 -m json.tool | grep http
   ```

3. **WSL2 memory config**: Add a `README.md` in the observability directory with these setup instructions:
   ```
   # WSL2 Setup (required on Windows host)
   Create C:\Users\<YourUser>\.wslconfig with:
   [wsl2]
   memory=12GB
   processors=4

   Then restart WSL: wsl --shutdown
   ```

4. **Promtail on Windows/WSL2**: Promtail uses `/var/run/docker.sock`. On Docker Desktop for Windows, the socket is accessible at the default path. If it fails, the fallback is to point Promtail at a log file directory instead.

---

## 🔍 Mandatory 2-Pass Self-Review

After generating all files, perform two review passes:

### Pass 1 — Wiring & Ports
- Verify `alertmanager.yml` webhook URL contains the `<RCA_ENGINE_HOST>` placeholder (not a hardcoded IP)
- Verify Grafana is on port `3001` (not `3000`, which is reserved for the Next.js dashboard)
- Verify `prometheus.yml` scrapes `otel-collector:8889` (not the services directly)
- Verify `otel-collector-config.yaml` exports to `jaeger:4317` via gRPC (not HTTP)
- Verify all 7 Docker Compose services are on `observability-net`
- Verify `scrape_interval: 1s` and `evaluation_interval: 1s` in `prometheus.yml`

### Pass 2 — Latency Tuning
- Verify `group_wait: 0s` in `alertmanager.yml` (not `1s` like v1)
- Verify `chunk_idle_period: 100ms` in `loki-config.yaml`
- Verify `batchwait: 100ms` in `promtail-config.yaml`
- Verify `--storage.tsdb.retention.time=2h` in Prometheus command args
- Verify `MEMORY_MAX_TRACES=5000` on Jaeger to cap RAM usage

Document any fixes you make during each pass.

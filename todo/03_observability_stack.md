# Task: Build the v2 Observability Stack (Single Machine)

## Context & Objective
You are operating within the Colony PS3 Distributed AI Observability project (`/home/xd/Coding/colony_ps3/`). This is a sub-5-second anomaly detection and auto-remediation pipeline. Everything runs on a **single machine** (i5-12H, 16GB RAM, RTX 3050, Linux).

Your job is to build the **complete observability stack** as a self-contained `docker-compose.yml` + all supporting config files. All services — microservices, observability, ML engine, and dashboard — run on the same Docker bridge network on this machine.

**Do NOT** touch the microservices (`v2/microservices/`), the ML engine, the dashboard, or the load generator. Only build the observability layer.

---

## Reference Material

A working v1 implementation lives at:
- `/home/xd/Coding/colony_ps3/v1/observability/` — study all config files carefully
- `/home/xd/Coding/colony_ps3/v1/deploy/docker-compose.yml` — the v1 compose file

Your v2 configs MUST carry over the aggressive v1 tuning (1s scrape, 100ms Promtail flush, aggressive Loki ingestion) and improve on it as detailed below.

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

All containers run on a single bridge network named `colony-net`. Other stacks (microservices, ML engine, dashboard) must also connect to `colony-net` as an **external** network.

```
[9 Microservices — same Docker network]
    ├── OTLP HTTP (traces+metrics) → otel-collector:4318
    └── stdout JSON logs → Promtail (via Docker socket)

[otel-collector] → Prometheus (metrics scrape at :8889)
                 → Jaeger (traces via OTLP gRPC)
                 → Loki (logs via OTLP)

[Prometheus] → Alertmanager → webhook → intelligence:5000 (RCA engine, same network)

[Grafana] ← queries Prometheus + Loki + Jaeger

Exposed host ports:
  OTel Collector: 4317, 4318
  Prometheus:     9090
  Alertmanager:   9093
  Loki:           3100
  Jaeger UI:      16686
  Grafana:        3001   ← 3001 to avoid clash with Next.js dashboard on 3000
```

---

## File 1: `docker-compose.yml`

### Network Declaration
Declare `colony-net` as an **external** network at the top level. This is critical — it allows other docker-compose stacks (microservices, ML engine, dashboard) to join the same network.

```yaml
networks:
  colony-net:
    external: true
```

> NOTE: Before running this stack, the user must create the network first with: `docker network create colony-net`
> Add this as a comment at the top of the compose file.

### Services (7 total)

**`otel-collector`**
- Image: `otel/opentelemetry-collector-contrib:0.97.0` (MUST use `contrib` — it has the Loki exporter)
- Command: `["--config=/etc/otel-collector-config.yaml"]`
- Config volume: `./otel-collector-config.yaml:/etc/otel-collector-config.yaml`
- Ports: `4317:4317`, `4318:4318`, `8889:8889`
- `depends_on: [loki, jaeger, prometheus]`

**`prometheus`**
- Image: `prom/prometheus:v2.51.0`
- Command: `--config.file=/etc/prometheus/prometheus.yml`, `--web.enable-lifecycle`, `--storage.tsdb.retention.time=2h`, `--storage.tsdb.retention.size=500MB`
- Volumes: `./prometheus.yml:/etc/prometheus/prometheus.yml`, `./rules.yml:/etc/prometheus/rules.yml`
- Port: `9090:9090`

**`alertmanager`**
- Image: `prom/alertmanager:v0.27.0`
- Command: `--config.file=/etc/alertmanager/alertmanager.yml`
- Volume: `./alertmanager.yml:/etc/alertmanager/alertmanager.yml`
- Port: `9093:9093`
- `depends_on: [prometheus]`

**`loki`**
- Image: `grafana/loki:2.9.8`
- Command: `-config.file=/etc/loki/loki-config.yaml`
- Volume: `./loki-config.yaml:/etc/loki/loki-config.yaml`
- Port: `3100:3100`

**`jaeger`**
- Image: `jaegertracing/all-in-one:1.56`
- Environment: `COLLECTOR_OTLP_ENABLED=true`, `SPAN_STORAGE_TYPE=memory`, `MEMORY_MAX_TRACES=5000`
- Ports: `16686:16686` (UI), `4317` (internal only — no host binding, other containers use service name)

**`promtail`**
- Image: `grafana/promtail:2.9.8`
- Command: `-config.file=/etc/promtail/promtail-config.yaml`
- Volumes: `./promtail-config.yaml:/etc/promtail/promtail-config.yaml`, `/var/run/docker.sock:/var/run/docker.sock:ro`, `/var/log:/var/log:ro`
- No external ports needed

**`grafana`**
- Image: `grafana/grafana:10.4.0`
- Port: `3001:3000`
- Environment:
  - `GF_SECURITY_ADMIN_PASSWORD=colony123`
  - `GF_USERS_ALLOW_SIGN_UP=false`
  - `GF_AUTH_ANONYMOUS_ENABLED=true`
  - `GF_AUTH_ANONYMOUS_ORG_ROLE=Viewer`
- Volumes:
  - `./grafana/provisioning:/etc/grafana/provisioning`
  - `./grafana/dashboards:/var/lib/grafana/dashboards`
- `depends_on: [prometheus, loki, jaeger]`

---

## File 2: `otel-collector-config.yaml`

Carry over v1 exactly, but use `otel-collector-contrib` Loki exporter syntax:

```yaml
receivers:
  otlp:
    protocols:
      grpc:
        endpoint: 0.0.0.0:4317
      http:
        endpoint: 0.0.0.0:4318

processors:
  batch:
    timeout: 200ms
    send_batch_size: 100
  resource:
    attributes:
      - key: service
        from_attribute: service.name
        action: insert
      - key: app
        from_attribute: service.name
        action: insert

exporters:
  prometheus:
    endpoint: "0.0.0.0:8889"
    namespace: ""
    resource_to_telemetry_conversion:
      enabled: true

  otlp/jaeger:
    endpoint: "jaeger:4317"
    tls:
      insecure: true

  loki:
    endpoint: "http://loki:3100/loki/api/v1/push"
    default_labels_enabled:
      exporter: false
      job: false
    labels:
      attributes:
        app: "app"
        service: "service"
        level: "level"
        error_type: "error_type"

service:
  pipelines:
    traces:
      receivers: [otlp]
      processors: [resource, batch]
      exporters: [otlp/jaeger]
    metrics:
      receivers: [otlp]
      processors: [resource, batch]
      exporters: [prometheus]
    logs:
      receivers: [otlp]
      processors: [resource, batch]
      exporters: [loki]
```

> Note: `level` and `error_type` are promoted as Loki labels because the v2 microservices emit them in their JSON logs and the RCA engine uses them for targeted LogQL queries.

---

## File 3: `prometheus.yml`

```yaml
global:
  scrape_interval: 1s       # v2: faster than v1's 2s
  evaluation_interval: 1s   # v2: evaluate rules every second

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
      # Map OTel's job label → service label so RCA webhook gets {"service": "payment-service"}
      - source_labels: [job]
        target_label: service
        action: replace
```

---

## File 4: `rules.yml`

```yaml
groups:
  - name: "v2-anomaly-detection"
    # NOTE: No 'for:' clause on any rule — instant triggering for sub-5s latency budget
    rules:
      - alert: HighErrorRate
        expr: rate(http_server_request_count_total{http_status_code=~"5.."}[30s]) > 0.1
        labels:
          severity: critical
          metric: http_server_request_count_total
        annotations:
          description: "Service {{ $labels.service }} is returning >10% 5xx errors."

      - alert: LatencySpike
        expr: histogram_quantile(0.95, rate(http_server_duration_milliseconds_bucket[30s])) > 2000
        labels:
          severity: critical
          metric: http_server_duration_milliseconds
        annotations:
          description: "Service {{ $labels.service }} P95 latency exceeded 2000ms."

      - alert: HighRequestErrorCount
        expr: increase(http_server_request_count_total{http_status_code=~"5.."}[30s]) > 5
        labels:
          severity: critical
          metric: http_server_request_count_total
        annotations:
          description: "Service {{ $labels.service }} had >5 errors in the last 30s."
```

> **IMPORTANT COMMENT TO ADD IN FILE**: OTel FastAPIInstrumentor metric names may vary by SDK version. Run this after first boot to verify exact names: `curl -s http://localhost:9090/api/v1/label/__name__/values | python3 -m json.tool | grep -i http`

---

## File 5: `alertmanager.yml`

```yaml
route:
  group_by: ['alertname', 'service']
  group_wait: 0s          # v2: instant dispatch (was 1s in v1)
  group_interval: 10s
  repeat_interval: 2m
  receiver: 'rca-engine-webhook'

receivers:
  - name: 'rca-engine-webhook'
    webhook_configs:
      # intelligence = the RCA engine container on the same colony-net network
      - url: 'http://intelligence:5000/alert'
        send_resolved: true
        http_config:
          timeout: 3s
```

---

## File 6: `loki-config.yaml`

```yaml
auth_enabled: false

server:
  http_listen_port: 3100
  grpc_listen_port: 9096
  log_level: warn

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
  reject_old_samples_max_age: 2h
  per_stream_rate_limit: 50MB
  per_stream_rate_limit_burst: 100MB

ingester:
  chunk_idle_period: 100ms   # CRITICAL: flush every 100ms for low RCA query latency
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

```yaml
server:
  http_listen_port: 9080
  grpc_listen_port: 0

positions:
  filename: /tmp/positions.yaml

clients:
  - url: http://loki:3100/loki/api/v1/push
    batchwait: 100ms    # CRITICAL: flush every 100ms
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

---

## Files 8 & 9: Grafana Provisioning

**`grafana/provisioning/datasources/datasources.yaml`**:
```yaml
apiVersion: 1
datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
  - name: Loki
    type: loki
    access: proxy
    url: http://loki:3100
  - name: Jaeger
    type: jaeger
    access: proxy
    url: http://jaeger:16686
```

**`grafana/provisioning/dashboards/dashboards.yaml`**:
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

Generate a valid Grafana dashboard JSON (schema version 36) with these 5 panels arranged in a 2-column grid. Dashboard title: `Colony PS3 — Service Overview`, uid: `colony-ps3-overview`, dark theme.

| Panel | Type | Query |
|-------|------|-------|
| Request Rate per Service | timeseries | `rate(http_server_request_count_total[30s])` by `service` |
| P95 Latency (ms) | timeseries | `histogram_quantile(0.95, rate(http_server_duration_milliseconds_bucket[30s]))` by `service` |
| 5xx Error Rate | timeseries | `rate(http_server_request_count_total{http_status_code=~"5.."}[30s])` by `service` |
| Active Alerts | alertlist | All firing alerts |
| Live Error Logs | logs | `{app=~".+", level="error"}` |

---

## 🔍 Mandatory 2-Pass Self-Review

### Pass 1 — Wiring & Ports
- `colony-net` declared as `external: true` in docker-compose.yml
- A comment at the top of docker-compose.yml tells the user to run `docker network create colony-net` first
- `otel-collector` uses `contrib` image (not base image — base has no Loki exporter)
- Alertmanager webhook URL points to `http://intelligence:5000/alert` (same Docker network, service name)
- Grafana on port `3001` (not `3000`)
- Jaeger port `4317` has no host binding (internal only)
- All 7 services are on `colony-net`

### Pass 2 — Latency Tuning
- `scrape_interval: 1s` and `evaluation_interval: 1s` in `prometheus.yml`
- `group_wait: 0s` in `alertmanager.yml`
- `chunk_idle_period: 100ms` in `loki-config.yaml`
- `batchwait: 100ms` in `promtail-config.yaml`
- `MEMORY_MAX_TRACES=5000` on Jaeger
- `--storage.tsdb.retention.time=2h` in Prometheus command
- `level` and `error_type` promoted as Loki labels in both `otel-collector-config.yaml` and `promtail-config.yaml`

Document any fixes you make during each pass.

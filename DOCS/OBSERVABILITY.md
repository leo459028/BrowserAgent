# Observability & Alerting Architecture

BrowserAgent provides comprehensive observability across the lifecycle of browser automation, distributed tracing, operational alerting, and agent safety telemetry.

---

## Operations & Health Check Endpoints

| Endpoint | Access Level | Description |
| :--- | :--- | :--- |
| `GET /healthz` | Public | Liveness probe verifying the API process is alive. |
| `GET /readyz` | Public | Database readiness probe verifying relational store connectivity. |
| `GET /v1/ops/readiness` | Operator / Admin | Comprehensive readiness diagnostic covering PostgreSQL, Kafka, Redis, S3, OIDC, and OTLP. |
| `GET /v1/ops/alerts` | Operator / Admin | Real-time evaluation of 7 operational reliability rules. |
| `GET /v1/ops/kms/status` | Operator / Admin | Reports Session Vault KMS envelope encryption status and round-trip benchmark latencies. |
| `GET /v1/ops/queues` | Operator / Admin | Real-time queue depths across priority topics (`high`, `queued`, `batch`) and worker pool bindings. |
| `GET /v1/ops/dlp/status` | Operator / Admin | Active Zero-Trust DLP status, regex rule catalogs, and masking policies. |
| `GET /v1/ops/federation/nodes` | Operator / Admin | Multi-cluster federation topology, node heartbeats, and leader lease status. |
| `POST /v1/ops/federation/heartbeat` | Public / Internal | Periodic node heartbeat registration and active schedule counters. |
| `POST /v1/ops/federation/re-election` | Admin | Manually triggers leadership re-election for disaster recovery drills. |
| `POST /v1/tasks/{id}/pause` | Operator / Admin | Suspends autonomous execution and switches to interactive HITL mode. |
| `POST /v1/tasks/{id}/interact` | Operator / Admin | Injects mouse click, text type, or key press actions into the live browser instance. |
| `POST /v1/tasks/{id}/resume` | Operator / Admin | Resumes automation and logs human intervention audit duration. |
| `POST /v1/tasks/matrix` | Creator / Admin | Dispatches concurrent multi-engine tasks across Chromium, Firefox, and WebKit. |
| `GET /v1/tasks/matrix/{matrix_id}` | Authenticated | Aggregated cross-engine status, execution times, verdicts, and screenshots. |
| `GET /v1/ops/traces/{trace_id}` | Operator / Admin | End-to-end distributed trace inspector returning hierarchical span call graphs. |
| `GET /v1/ops/otlp/status` | Operator / Admin | Reports OpenTelemetry OTLP Batch Span Exporter telemetry metrics. |
| `POST /v1/ops/otlp/flush` | Admin | Immediately flushes all buffered trace spans to external OTLP collectors. |
| `POST /v1/ops/alerts/test-dispatch` | Admin | Dispatches an immediate test alert to Slack/Discord webhooks. |
| `WS /v1/tasks/{task_id}/live-stream` | Authenticated | Low-latency JPEG frame broadcasting via WebSockets at 2 FPS. |
| `GET /v1/sessions/{session_name}/validate`| Operator / Admin | Performs cryptographic decryption round-trip verifying stored credential integrity. |
| `GET /metrics` | Operator / Admin | Prometheus-formatted metrics scrape endpoint. |

---

## Prometheus Operational Metrics

Exposed via `GET /metrics`:

- `browser_agent_tasks_created_total`: Total automation tasks created, partitioned by risk tier and engine.
- `browser_agent_tasks_executed_total`: Total task execution attempts.
- `browser_agent_tasks_failed_total`: Total failed tasks.
- `browser_agent_tasks_dlq_total`: Counter of tasks routed to the Dead Letter Queue.
- `browser_agent_task_duration_seconds`: Histogram of browser execution latencies.
- `browser_agent_http_requests_total`: Total incoming HTTP requests partitioned by path and status code.
- `browser_agent_http_request_duration_seconds`: HTTP request latency histogram.
- `browser_agent_auth_failures_total`: Total authentication/authorization rejections.
- `browser_agent_production_readiness`: Gauge indicating production hardening compliance (1 = ready, 0 = degraded/not ready).

---

## Multi-Priority Queues Telemetry

Monitored in real time via `GET /v1/ops/queues`:
- **Queue Depths**: Live monitoring of unconsumed backlogs across `agent.tasks.high`, `agent.tasks.queued`, and `agent.tasks.batch`.
- **Traffic Routing Counters**: Cumulative counts for `high_priority_routed`, `normal_priority_routed`, and `batch_priority_routed`.
- **Worker Pool Subscriptions**: Active worker pool identifier (`WORKER_POOL_NAME`) and list of subscribed Kafka topics.

---

## Live Stream & Takeover Telemetry

- **Broadcast Queue Depth**: `LiveTelemetryService` tracks active frame queues and connected viewer counts.
- **Asynchronous Transmission**: Broadcasts Base64 JPEG frames at 2 FPS over WebSockets without blocking the main Playwright automation loop.
- **Lifecycle Events**: Broadcasts `step_started`, `self_healed`, `task_finished`, and `aborted` events in real time.

---

## Selector Self-Healing Telemetry

- **Self-Healing Flag**: Tasks and steps recovering via the 3-tier fallback cascade are marked with `self_healed: true`.
- **Audit Trails**: Generates structured `task.self_healed` audit events detailing the original failed selector, the recovered selector, the strategy used (`semantic_attribute`, `text_match`, `dom_structure`), and confidence score.
- **Operations Console Badge**: Visualized with a green `Self-Healed ✓` badge in the Visual Step Replay view.

---

## KMS Envelope Encryption Health

Exposed via `GET /v1/ops/kms/status`:
- Operational health (`healthy` / `degraded`).
- Active KMS driver (`local`, `aws`, `vault`).
- Key Encryption Key (KEK) identifier and algorithm (`AES-256-GCM`).
- Real-time encryption/decryption round-trip benchmark latency (`roundtrip_ms`).

---

## Distributed Tracing & W3C Context Propagation

1. **Context Propagation**:
   - The API middleware extracts or creates W3C `traceparent` headers (`00-{trace_id}-{span_id}-{flags}`), echoing them back in HTTP response headers alongside `X-Correlation-ID`.
   - Injected into Kafka event payloads under `trace_context`.
   - Workers resume the trace context, creating child execution spans.
2. **Span Lifecycle**:
   - Tracks `trace_id`, `span_id`, `parent_span_id`, `name`, `service_name`, timestamps, duration, status, and custom attributes.
3. **Trace Inspector**:
   - The Operations Center queries `GET /v1/ops/traces/{trace_id}`, merging in-memory trace buffers and database step records into a unified span tree.

---

## OpenTelemetry OTLP Streaming

The `OtlpBatchSpanExporter` continuously exports trace telemetry:
- **Protocol**: Standard OTLP HTTP/JSON format (`POST /v1/traces`), fully compatible with Jaeger, Grafana Tempo, Datadog Agent, and OpenTelemetry Collector.
- **Asynchronous Batching**: Enqueues spans in memory and flushes in batches upon reaching `OTEL_BATCH_SIZE` (default: 50) or flush timeout.
- **Queue Overflow Protection**: Ring buffer ceiling (default: 2,000 spans). If the downstream APM collector becomes unreachable, excess spans are safely dropped to prevent memory leaks or process crashes.
- **Management API**: Query status via `GET /v1/ops/otlp/status` or force immediate evacuation with `POST /v1/ops/otlp/flush`.

---

## Production Alerting Center (7 Operational Rules)

Evaluated in real time via `GET /v1/ops/alerts`:

| Rule ID | Severity | Evaluation Condition | Recommended Remediation |
| :--- | :--- | :--- | :--- |
| `dlq_backlog_critical` | Critical | DLQ backlog >= 5 failed tasks | Inspect worker error logs and replay or quarantine tasks. |
| `task_failure_rate_warning` | Warning | Recent task failure rate >= 30% | Verify target website accessibility or locator changes. |
| `pending_approval_backlog_info` | Info | Pending approval tasks >= 10 | Prompt designated Approvers to review pending workflows. |
| `worker_liveness_critical` | Critical | Time since last task execution > 15m (with queue backlog) | Check worker container health and Kafka connectivity. |
| `db_latency_warning` | Warning | Database ping latency > 200ms | Inspect PostgreSQL host CPU/memory and connection pool. |
| `reliability_memory_fallback_warning` | Warning | Production environment running in-memory reliability store | Switch `RELIABILITY_STORE` to `redis`. |
| `webhook_unconfigured_info` | Info | External alert webhook URL not configured | Configure `ALERT_WEBHOOK_URL` to enable outbound alerts. |

- **Non-blocking Webhooks**: Warning and Critical alerts trigger asynchronous background HTTP dispatches to Slack/Discord webhooks with a 3-second timeout.
- **Channel Verification**: Operators can test webhook delivery at any time via `POST /v1/ops/alerts/test-dispatch`.

---

## Visual Step Replay & Video Playback

Endpoints `GET /v1/tasks/{task_id}/replay` and `GET /v1/tasks/{task_id}/video` provide comprehensive reproducibility:
- **Step Navigation Tabs**: Step-by-step tabs (Step 1, Step 2, ...) in the Operations Center.
- **Interactive Previews**: Displays step type, status, duration in milliseconds, associated span ID, DOM summary, and screenshot thumbnails.
- **Full-Motion WebM Video**: Native HTML5 player streaming full-screen browser recordings directly from `/v1/tasks/{task_id}/video`.

---

## Human-in-the-Loop (HITL) Observability

- **State Badges**: Real-time status indicator (`AUTOMATED`, `PAUSED (TAKEOVER)`, `RESUMED`).
- **Intervention Auditing**:
  - `task.human_intervened = True` marks tasks requiring human assistance.
  - Audit logs record operator email, pause reason, pause timestamp, resume timestamp, and total intervention duration (`duration_seconds`).
  - Every individual mouse click (coordinates X, Y) or keystroke is audited as `task.interacted`.

---

## Cross-Browser Matrix Observability

- **Unified Dashboard**: Aggregated cross-engine status queried via `GET /v1/tasks/matrix/{matrix_id}`.
- **Metrics Comparison Matrix**:
  - Side-by-side execution duration (ms) across Chromium, Firefox, and WebKit.
  - Verdict scores (`pass` / `fail`) under identical verification conditions.
  - Identification of engine-specific DOM self-healing triggers or rendering anomalies.

---

## Zero-Trust DLP & Federation Observability

- **DLP Status**: `GET /v1/ops/dlp/status` reports active regex filters, CSS blur status, and redaction counts.
- **DLP Task Flag**: Persisted with `task.dlp_masked = True` and highlighted with the `DLP Shield: Active` badge.
- **Cluster Topology**: `GET /v1/ops/federation/nodes` monitors node heartbeats, active schedule distributions, and leader lease expirations across geographic regions.

# API Specification

Base URL:

```text
http://localhost:8000
```

BrowserAgent enforces multi-tier Authentication and Role-Based Access Control (RBAC). Except for public endpoints (`/healthz`, `/readyz`, `/operations`, `/v1/auth/oidc/*`, and the local token endpoint), all requests require:

```text
Authorization: Bearer <JWT>
```
or an active HttpOnly `ba_session` cookie issued via OIDC SSO.

---

## Authentication & Identity

### `POST /v1/auth/local-token`

Issues signed HS256 local developer tokens for development and testing. Enabled only when `AUTH_LOCAL_TOKENS_ENABLED=true`.

**Request**:
```json
{
  "role": "operator"
}
```

*Available roles*: `creator`, `approver`, `operator`, `admin`.

### `GET /v1/auth/me`

Returns the current authenticated actor context and assigned roles.
- `AUTH_MODE=local`: Verifies local dev tokens using `APP_SECRET_KEY` (HS256).
- `AUTH_MODE=jwks`: Verifies RS256 JWTs using public keys fetched from `AUTH_JWKS_URL` or derived from `AUTH_OIDC_ISSUER_URL`.
- Supports credentials supplied via either `Authorization: Bearer <token>` or the HttpOnly `ba_session` cookie.

### `GET /v1/auth/oidc/login`

Public endpoint. Initiates the Enterprise OIDC Authorization Code Flow with PKCE:
- Generates a cryptographically random PKCE `code_verifier` and SHA-256 `code_challenge`.
- Generates a CSRF-preventing `state` parameter and stores transient verification keys in the cache.
- Returns HTTP 307 redirecting the user to the IdP authorization endpoint (`AUTH_OIDC_AUTHORIZATION_ENDPOINT` or discovered issuer URL).

### `GET /v1/auth/oidc/callback`

Public callback endpoint. Receives authorization `code` and `state` parameters from the identity provider:
- Validates the `state` against session cache to prevent CSRF.
- Exchanges the authorization code and stored `code_verifier` for tokens at the IdP Token endpoint.
- Validates token signatures and claims, issues a secure HttpOnly `ba_session` cookie, logs an `auth.oidc_callback_success` audit entry, and redirects the browser back to `/operations`.

---

## Operations & Platform Health

### `GET /operations`

Renders the **Browser Agent Operations Center** web console. Provides operational access to task management, approvals, production readiness diagnostics, alert rule evaluations, distributed trace inspection, visual step replay, live WebSockets streaming, Session Vault credentials, and cluster federation topology.

*Automatic path redirects*:
- `GET /` ➜ 307 Redirect to `/operations`
- `GET /operation` ➜ 307 Redirect to `/operations`

### `GET /v1/ops/readiness`

Requires `operator` or `admin` role. Returns comprehensive diagnostic checks covering database connectivity, message bus health, artifact backend availability, worker identity, DLQ configurations, production readiness checks, and OpenTelemetry instrumentation state.

**Key Response Fields**:
- `production.status`: `ready`, `degraded`, or `not_ready`.
- `production.checks`: Evaluates disabled local tokens, secret key strength, JWKS/OIDC configurations, Redis reliability, Kafka, and S3 artifact backends.
- `observability.otel_ready`: Indicates log and request schemas have reserved OpenTelemetry fields.
- `observability.log_schema_fields`: Standardized correlation fields included in logs.
- `kubernetes`: `{"in_cluster": bool, "manifests_available": bool}`.
- `otlp`: `{"enabled": bool, "endpoint": str, "queue_size": int, "dropped_spans": int, "exported_spans": int}`.

### `GET /v1/ops/kms/status`

Requires `operator` or `admin` role. Reports health and metrics for the Session Vault KMS envelope encryption engine:
- `status`: `healthy` or `degraded`.
- `provider`: Active driver (`local`, `aws`, `vault`).
- `key_id`: Active Key Encryption Key (KEK) identifier (e.g., `local-kek-v1`).
- `algorithm`: `AES-256-GCM`.
- `test_encryption`: `{"ok": true, "roundtrip_ms": float}` real-time encryption/decryption round-trip benchmark.

### `GET /v1/ops/queues`

Requires `operator` or `admin` role. Monitors multi-priority queue backlogs and worker pool isolation:
- `queues`: Real-time queue depths across priority topics (`agent.tasks.high`, `agent.tasks.queued`, `agent.tasks.batch`).
- `worker_pool`: Active worker pool name and subscribed topics.
- `metrics`: Counts for `high_priority_routed`, `normal_priority_routed`, and `batch_priority_routed`.

### `GET /v1/ops/alerts`

Requires `operator` or `admin` role. Real-time evaluation of 7 operational reliability rules:
- `evaluation_time`: ISO 8601 evaluation timestamp.
- `summary`: `{"critical": int, "warning": int, "info": int, "healthy": bool}`.
- `metrics_snapshot`: Failure rates, DLQ backlog size, pending approval count, worker heartbeats, and database query latencies.
- `alerts`: List of triggered alert items (containing `rule_id`, `severity`, `message`, `metric_name`, `metric_value`, `threshold`, `recommendation`).
- `webhook_enabled`: Whether Slack/Discord external webhook forwarding is configured.

### `POST /v1/ops/alerts/test-dispatch`

Requires `admin` role. Dispatches an immediate test notification to configured Slack/Discord webhooks and records an audit log entry.

**Request Body**:
```json
{
  "rule_id": "test_alert",
  "severity": "info",
  "message": "Manual test notification from operations center"
}
```

### `GET /v1/ops/traces/{trace_id}`

Requires `operator` or `admin` role. Retrieves the end-to-end distributed trace spanning API control plane calls and worker execution steps:
- `trace_id`: 32-character hexadecimal trace identifier.
- `span_count`: Total associated spans.
- `root_service`: Ingress service name.
- `spans`: Hierarchical list of spans (including `span_id`, `parent_span_id`, `name`, `service_name`, timestamps, duration, status, attributes, and events).

### `GET /v1/ops/otlp/status`

Requires `operator` or `admin` role. Reports current telemetry streaming status for the OpenTelemetry OTLP Batch Span Exporter.

### `POST /v1/ops/otlp/flush`

Requires `admin` role. Immediately drains and flushes pending memory trace spans to the external OTLP receiver.

---

## Health & System Telemetry

- `GET /healthz`: Public liveness probe.
- `GET /readyz`: Public database readiness probe.
- `GET /metrics`: Requires `operator` or `admin` role. Returns Prometheus-compatible operational counters and latencies.

All HTTP responses propagate the `X-Correlation-ID` header. The platform also parses W3C `traceparent` headers to correlate cross-process trace contexts.

---

## Task Lifecycle & Governance

### `POST /v1/tasks`

Requires `creator` or `admin` role. Submits an automation task with optional `Idempotency-Key` header. Duplicate submissions with identical keys and payloads return the existing task; conflicting payloads return HTTP 409.

**Request**:
```json
{
  "title": "Audit Compliance Dashboard",
  "instructions": "Navigate to the partner portal and capture proof of active license.",
  "priority": 1,
  "risk_level": "medium",
  "browser_engine": "chromium",
  "metadata": {
    "start_url": "https://example.com/portal",
    "domains": ["example.com"]
  }
}
```

### `GET /v1/tasks`

Requires authenticated actor. Lists recent tasks within the actor's tenant.

### `GET /v1/tasks/{task_id}`

Requires authenticated actor. Retrieves detailed task status and execution results for a tenant-scoped task.

### `POST /v1/tasks/{task_id}/approve`

Requires `approver` or `admin` role. Transitions a task from `pending_approval` to `queued`, routing it to the appropriate priority Kafka topic.

### `GET /v1/tasks/{task_id}/audit`

Requires `approver`, `operator`, or `admin` role. Returns an immutable timeline of audit events associated with the task.

### `GET /v1/tasks/{task_id}/replay`

Requires `approver`, `operator`, or `admin` role. Returns visual step replay and video metadata:
- `task_id`: Task identifier.
- `trace_id`: Associated distributed trace ID.
- `video_artifact_id`: Artifact identifier for the full-session WebM video recording.
- `video_url`: Direct video streaming URL (`/v1/tasks/{task_id}/video`).
- `steps_visual`: Array of executed steps containing duration, DOM summaries, span IDs, and screenshot artifact references.
- `evaluation_summary`: Verdict evaluation summary.
- `timeline`: Normalized event timeline combining audit entries, steps, and artifacts.

### `GET /v1/tasks/{task_id}/video`

Requires authenticated actor. Streams the recorded full-motion browser execution video (`video/webm`).

### `WS /v1/tasks/{task_id}/live-stream`

Requires authenticated actor. WebSocket connection providing real-time browser frame streaming:
- Streams base64-encoded JPEG frames (`{"type": "frame", "frame_id": int, "timestamp": str, "data": "data:image/jpeg;base64,..."}`).
- Broadcasts step transitions and self-healing events (`{"type": "event", "event": "step_started", ...}`).
- Handles `ping`/`pong` keepalive messages.
- Dispatches termination events upon completion (`{"type": "task_finished", "status": "completed|failed|aborted"}`).

### `POST /v1/tasks/{task_id}/abort`

Requires `operator` or `admin` role. Online cancellation of a running task. The worker detects the abort flag, safely terminates Playwright browser contexts, records an audit entry, and sets the task status to `aborted`.

---

## Human-in-the-Loop (HITL) Remote Takeover

### `POST /v1/tasks/{task_id}/pause`

Requires `operator` or `admin` role. Suspends autonomous execution loop and enters interactive HITL mode:

```json
{
  "reason": "Resolve interactive Cloudflare challenge"
}
```

### `POST /v1/tasks/{task_id}/interact`

Requires `operator` or `admin` role. Injects manual human interactions into the live browser instance.

**Click Action**:
```json
{
  "action": "click",
  "x": 350.5,
  "y": 210.0
}
```

**Type Action**:
```json
{
  "action": "type",
  "text": "secure_verification_code_456"
}
```

**Key Press Action**:
```json
{
  "action": "press",
  "key": "Enter"
}
```

### `POST /v1/tasks/{task_id}/resume`

Requires `operator` or `admin` role. Resumes the automated execution loop. Marks the task with `human_intervened = true`, records total intervention duration, and logs operator identity.

---

## Cross-Browser Matrix Execution

### `POST /v1/tasks/matrix`

Requires `creator` or `admin` role. Dispatches a unified task concurrently across Chromium, Firefox, and WebKit browser engines.

**Request**:
```json
{
  "title": "Checkout Flow Cross-Browser Layout Verification",
  "instructions": "Navigate to checkout, fill input fields, verify price summary",
  "priority": 1,
  "risk_level": "low",
  "engines": ["chromium", "firefox", "webkit"],
  "metadata": {
    "start_url": "https://example.com/checkout"
  }
}
```

**Response**:
```json
{
  "matrix_id": "matrix-9c3f2e1a4b8d",
  "total_tasks": 3,
  "tasks": [
    {
      "task_id": "acb1ceb5-84b6-4ecf-bdcf-9c0c3d547956",
      "browser_engine": "chromium",
      "status": "pending_approval",
      "title": "[Chromium] Checkout Flow Cross-Browser Layout Verification"
    },
    {
      "task_id": "2893b283-9402-4d41-84c4-a8bb4499221d",
      "browser_engine": "firefox",
      "status": "pending_approval",
      "title": "[Firefox] Checkout Flow Cross-Browser Layout Verification"
    },
    {
      "task_id": "3655d0c8-5308-4ec0-a1a7-90dd7607e6be",
      "browser_engine": "webkit",
      "status": "pending_approval",
      "title": "[Webkit] Checkout Flow Cross-Browser Layout Verification"
    }
  ]
}
```

### `GET /v1/tasks/matrix/{matrix_id}`

Requires authenticated actor. Retrieves aggregated cross-engine execution metrics, verdicts, duration differences, and screenshots.

---

## Zero-Trust Dynamic DLP (Data Loss Prevention)

### `GET /v1/ops/dlp/status`

Requires `operator` or `admin` role. Reports active DLP masking rules, regex sanitizers, and status:

**Response**:
```json
{
  "status": "active",
  "active_rules": [
    "password_kv",
    "bearer_token",
    "jwt_pattern",
    "openai_api_key",
    "aws_access_key",
    "private_key_pem",
    "credit_card"
  ],
  "mask_passwords": true,
  "redact_tokens": true,
  "description": "Zero-Trust DLP applies CSS gaussian blur to sensitive DOM fields and redacts secrets in texts and metadata."
}
```

---

## Multi-Cluster Scheduling Federation

### `GET /v1/ops/federation/nodes`

Requires `operator` or `admin` role. Returns cluster topology, node health, heartbeat latencies, and designated leader node.

### `POST /v1/ops/federation/heartbeat`

Invoked periodically by cluster nodes to renew distributed leadership leases:

```json
{
  "node_id": "cluster-node-tokyo-01",
  "region": "ap-northeast-1",
  "active_schedules_count": 8,
  "metadata": {"cpu_usage": 0.25, "memory_usage": 0.42}
}
```

### `POST /v1/ops/federation/re-election`

Requires `admin` role. Forces leadership migration to a specified backup node for maintenance or disaster recovery.

```json
{
  "target_node_id": "cluster-node-osaka-02"
}
```

---

## Scheduled Tasks Engine

- `POST /v1/scheduled-tasks`: Creates an automated Cron schedule.
- `GET /v1/scheduled-tasks`: Lists active schedules for the current tenant.
- `PATCH /v1/scheduled-tasks/{schedule_id}`: Modifies schedule parameters or pauses by setting `is_active: false`.
- `POST /v1/scheduled-tasks/{schedule_id}/run`: Manually dispatches an immediate run of a scheduled task.
- `POST /v1/scheduled-tasks/evaluate`: Manually triggers evaluation of all scheduled tasks.

---

## Session Vault Governance

- `GET /v1/sessions`: Lists all encrypted `storage_state` session credentials for the current tenant.
- `GET /v1/sessions/{session_name}/validate`: Validates cryptographic integrity and counts cookies/origins in the session payload.
- `DELETE /v1/sessions/{session_name}`: Marks session credentials as revoked, preventing future automatic reuse.

---

## Reliability, DLQ & Quarantine

- `GET /v1/reliability`: Retrieves reliability configuration and rate limits.
- `GET /v1/dlq/tasks`: Lists failed tasks present in the Dead Letter Queue.
- `POST /v1/dlq/tasks/{task_id}/replay`: Replays an individual failed DLQ task.
- `POST /v1/dlq/tasks/bulk-replay`: Bulk replays a list of failed tasks.
- `POST /v1/dlq/tasks/{task_id}/quarantine`: Isolates a poisoned task into quarantine.

---

## Artifact Storage & Access

### `GET /v1/artifacts/{artifact_id}/content`

Requires authenticated actor. Retrieves raw binary content (screenshots, HTML, traces). Enforces strict tenant boundaries and path traversal restrictions.

# Operations Runbook (v1.4.2)

This runbook outlines standard operating procedures for deploying, verifying, monitoring, and troubleshooting BrowserAgent across local Docker Compose, Kubernetes, and Helm environments.

---

## 1. Stack Initialization

Initialize environment configurations and spin up the containerized architecture:

```bash
cp .env.example .env
docker compose up -d --build
```

Execute Alembic database migrations:
```bash
docker compose exec -T api alembic upgrade head
```

Verify service status and readiness:
```bash
docker compose ps
curl http://127.0.0.1:8000/healthz
curl http://127.0.0.1:8000/readyz
```

---

## 2. Accessing the Operations Center

Open your web browser and navigate to:

```text
http://127.0.0.1:8000/operations
```

Verify the following UI components:
- **Title Bar**: `Browser Agent v1.4 Operations Center` with backward compatibility notice (`Browser Agent v1.2 Operations Center compatible`).
- **Header Badges**: `DLP Shield: Active`, `Cluster: Federation Online`, `Platform: K8s/Helm Ready`, `OTLP: Ready`, and `SSO Login with IdP`.
- **Create Task Card**: Browser Engine selector (`Chromium`, `Firefox`, `WebKit`), DLP protection toggle, and `Dispatch Matrix (3 Engines)` button.
- **Live Telemetry Stream Card**: Low-latency canvas viewer, `Abort Task` button, and HITL Takeover toolbar (`Pause (Takeover)`, `Resume Task`, `Send Keys`, `Remote Key Input`).
- **Cross-Browser Matrix Comparison Panel**: Aggregated side-by-side performance, duration deltas, self-healing status, and screenshots.
- **Zero-Trust Dynamic DLP Status Panel**: Regex rules catalog, Gaussian blur masking toggles, and token redaction metrics.
- **Multi-Cluster Scheduling Federation Panel**: Regional node heartbeats, leader lease status, and one-click forced re-election.
- **Scheduled Tasks Card**: Cron schedule manager, active toggles, and `Run Now` triggers.
- **Session Vault Card**: KMS-encrypted credentials list, `Validate` decryption round-trip, and `Revoke` button.
- **Priority Queues Telemetry Card**: Real-time depths across `High`, `Queued`, and `Batch` Kafka topics.
- **Production Alerting Center**: Real-time evaluation of 7 operational reliability rules and manual webhook test dispatch.
- **Trace Inspector**: Distributed trace hierarchy lookup by Trace ID.
- **Visual Step Replay**: Step tabs displaying execution timing (ms), DOM summaries, screenshots, and green `Self-Healed ✓` badges.

---

## 3. Authentication Verification Smoke Test

Acquire an operator developer token and verify identity:

```bash
TOKEN=$(curl -s -X POST http://127.0.0.1:8000/v1/auth/local-token \
  -H "Content-Type: application/json" \
  -d '{"role":"operator"}' | jq -r .access_token)

curl -s -X GET http://127.0.0.1:8000/v1/auth/me \
  -H "Authorization: Bearer $TOKEN"
```

---

## 4. Diagnostics & Production Hardening Audits

### Inspect System Readiness & Alerts
```bash
curl -s -X GET http://127.0.0.1:8000/v1/ops/readiness \
  -H "Authorization: Bearer $TOKEN"

curl -s -X GET http://127.0.0.1:8000/v1/ops/alerts \
  -H "Authorization: Bearer $TOKEN"
```

### Test Outbound Webhook Dispatch (Admin Role)
```bash
ADMIN_TOKEN=$(curl -s -X POST http://127.0.0.1:8000/v1/auth/local-token \
  -H "Content-Type: application/json" \
  -d '{"role":"admin"}' | jq -r .access_token)

curl -s -X POST http://127.0.0.1:8000/v1/ops/alerts/test-dispatch \
  -H "Authorization: Bearer $ADMIN_TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"rule_id":"test_alert","severity":"info","message":"Manual verification dispatch"}'
```

### Validate Production-Like Compose Configuration
```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

### Validate Kubernetes Manifests & Helm Charts
```bash
# Kustomize validation
kubectl kustomize deploy/k8s/

# Helm Chart linting and templating
helm lint deploy/helm/browser-agent
helm template browser-agent deploy/helm/browser-agent
```

---

## 5. End-to-End Task Lifecycle & Video Replay

1. In `/operations`, go to **`Create Task`**, select `Normal planner task`, and click **`Create task`**.
2. The task enters `pending_approval`. Select the task from the **`Recent Tasks`** list.
3. The **`Approve selected`** button switches to active bright green. Click to approve.
4. The assigned worker consumes the task, launches Playwright, and executes the navigation flow. Status transitions to `completed`.
5. Under **`Visual Step Replay`**, click individual step tabs to inspect duration (ms), DOM summaries, and screenshot thumbnails. If self-healing occurred, steps display a green `Self-Healed ✓` badge.
6. The **`Execution Video Recording`** card loads the full-session WebM video recording for playback.
7. Copy the task's Trace ID and paste it into the **`Trace Inspector`** to explore the hierarchical span tree.

---

## 6. Scheduled Tasks & Session Vault Operations

### Scheduled Tasks
1. Under **`Scheduled Tasks`**, click `Create Schedule`, entering a name and Cron expression (e.g., `0 9 * * *`).
2. Select the schedule and click **`Run Now`** to trigger immediate task dispatch.

### Session Vault
1. Under **`Session Vault`**, click **`Refresh Sessions`** to review encrypted `storage_state` credentials.
2. Click **`Validate`** to execute a real-time KMS decryption round-trip and verify AAD tenant integrity.
3. Click **`Revoke`** to mark a compromised or obsolete session as revoked.

---

## 7. Operational Drills: HITL, Matrix & Federation

### Bidirectional Remote Takeover (HITL) Drill
1. While a task is executing, click orange **`Pause (Takeover)`** (`POST /v1/tasks/{id}/pause`).
2. Verify status updates to **`PAUSED (TAKEOVER)`** and automated execution halts.
3. Click on the live stream canvas to inject a click (`POST /v1/tasks/{id}/interact` with `action: click`).
4. Enter text in `Remote Key Input` and click **`Send Keys`** to inject typing (`action: type`).
5. Click **`Resume Task`** (`POST /v1/tasks/{id}/resume`) to resume autonomous execution. Verify intervention duration is audited.

### Cross-Browser Matrix Execution Drill
1. In `Create Task`, click **`Dispatch Matrix (3 Engines)`** (`POST /v1/tasks/matrix`).
2. Approve the generated tasks.
3. In the **`Cross-Browser Matrix Comparison`** panel, review aggregated execution times, verdicts, self-healing triggers, and rendering differences across Chromium, Firefox, and WebKit.

### Multi-Cluster Federation Failover Drill
1. In the **`Multi-Cluster Scheduling Federation Topology`** panel, observe node heartbeats and the designated Leader node.
2. Click **`Force Re-election`** next to a standby node (`POST /v1/ops/federation/re-election`).
3. Verify leadership lease migrations immediately to the standby node without downtime.

---

## 8. Dead Letter Queue (DLQ) Remediation

- Query DLQ: Inspect failed tasks via `GET /v1/dlq/tasks`.
- Replay: Replay an individual task via `POST /v1/dlq/tasks/{id}/replay` or bulk replay via `POST /v1/dlq/tasks/bulk-replay`.
- Quarantine: Isolate poisonous payloads:
  ```bash
  curl -X POST http://127.0.0.1:8000/v1/dlq/tasks/<TASK_ID>/quarantine \
    -H "Authorization: Bearer $TOKEN" \
    -H "Content-Type: application/json" \
    -d '{"reason":"Poisonous task payload causing unrecoverable browser panic"}'
  ```

---

## 9. Troubleshooting & Recovery

### Kafka / Zookeeper Stale Sessions
If containers experience `NodeExists` or Zookeeper session timeout issues during rapid restarts:
```bash
docker compose restart zookeeper kafka api worker
```

### Full Automated Verification Suite
```bash
pytest -q
python -m compileall src tests worker alembic
git diff --check
docker compose exec -T api pytest -q
```

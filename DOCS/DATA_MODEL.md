# Data Model Specification

The database models are implemented using SQLAlchemy in [src/browser_agent/models.py](../src/browser_agent/models.py). Database schema migrations are managed via Alembic (up to `0004_v14_federation_and_matrix`), defining the `cluster_nodes` table, extended `tasks` execution columns (`browser_engine`, `matrix_id`, `human_intervened`, `dlp_masked`), `scheduled_tasks` scheduler table, and cryptographic `task_artifacts` governance.

---

## Seeded Local Developer Identities

`scripts/bootstrap.py` provisions deterministic local development tenants and user roles:

| Role | Email | UUID |
| :--- | :--- | :--- |
| **admin** | `ops@example.com` | `00000000-0000-0000-0000-000000000002` |
| **creator** | `creator@example.com` | `00000000-0000-0000-0000-000000000003` |
| **approver** | `approver@example.com` | `00000000-0000-0000-0000-000000000004` |
| **operator** | `operator@example.com` | `00000000-0000-0000-0000-000000000005` |

Default Tenant UUID: `00000000-0000-0000-0000-000000000001`

---

## Tasks Table (`tasks`) Extended Schema

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique task identifier. |
| `tenant_id` | UUID (FK) | Scoped tenant identifier. |
| `title` | Text | Human-readable title of the task. |
| `instructions` | Text | Autonomous natural language instructions for the browser agent. |
| `status` | Text | Task status (`pending_approval`, `queued`, `running`, `completed`, `failed`, `aborted`). |
| `risk_level` | Text | Evaluated risk tier (`low`, `medium`, `high`, `critical`). |
| `priority` | Integer | Priority weighting (`>0` high, `0` default, `<0` batch). |
| `browser_engine` | Text | Browser engine used for execution: `chromium`, `firefox`, or `webkit`. |
| `matrix_id` | Text (Nullable) | Correlation identifier linking multi-browser matrix runs. |
| `human_intervened` | Boolean | Flag indicating whether a human operator paused or interacted with the session. |
| `dlp_masked` | Boolean | Flag indicating whether Zero-Trust DLP visual blur or token redaction was applied. |
| `scheduled_task_id` | UUID (FK, Nullable) | Foreign key pointing to the originating Cron schedule if triggered automatically. |
| `metadata_` | JSON | Complete execution plan, evaluations, DLQ states, and telemetry metadata. |
| `created_by` | UUID (FK) | Creator actor identifier. |
| `approved_by` | UUID (FK, Nullable) | Approver actor identifier. |
| `created_at` | DateTime (UTC) | Creation timestamp. |
| `updated_at` | DateTime (UTC) | Last state transition timestamp. |

---

## Cluster Nodes Table (`cluster_nodes`)

Supports multi-cluster scheduling federation topology, heartbeat monitoring, and distributed lease locks:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Unique record identifier. |
| `node_id` | Text (Unique) | Human-readable cluster node identifier (e.g., `cluster-node-tokyo-01`). |
| `region` | Text | Geographic or cloud region label (e.g., `ap-northeast-1`). |
| `status` | Text | Liveness status (`online`, `degraded`, `offline`). |
| `is_leader` | Boolean | True if node currently holds the active scheduling leader lease. |
| `active_schedules_count` | Integer | Count of currently active schedules managed by this node. |
| `last_heartbeat` | DateTime (UTC) | Timestamp of the most recent heartbeat ping. |
| `metadata_` | JSON | Node runtime metrics (CPU, memory, pool capacity). |
| `created_at` | DateTime (UTC) | Initial registration timestamp. |
| `updated_at` | DateTime (UTC) | Timestamp of last node modification. |

---

## Scheduled Tasks Table (`scheduled_tasks`)

Maintains automated recurring browser inspection schedules:

| Column | Type | Description |
| :--- | :--- | :--- |
| `id` | UUID (PK) | Schedule identifier. |
| `tenant_id` | UUID (FK) | Scoped tenant identifier. |
| `name` | Text | Descriptive schedule name. |
| `cron_expression` | Text | Standard 5-field Cron expression (e.g., `0 9 * * *`). |
| `concurrency_policy` | Text | Reentrancy guard: `skip` (skips if prior run is unfinished) or `allow`. |
| `is_active` | Boolean | Master switch enabling or pausing schedule execution. |
| `task_template` | JSON | Template payload used to instantiate recurring task instances. |
| `last_run_at` | DateTime (UTC) | Timestamp of last dispatch. |
| `next_run_at` | DateTime (UTC) | Computed next run timestamp. |
| `created_by` | UUID (FK) | Creator actor identifier. |
| `created_at` | DateTime (UTC) | Creation timestamp. |
| `updated_at` | DateTime (UTC) | Last modification timestamp. |

---

## Task Metadata Specification

Stored in `tasks.metadata_`:

- `policy`: Policy evaluation verdict and reasoning.
- `planner`: Plan generation version, validation flags, and resolved skill capabilities.
- `plan`: Detailed browser interaction steps.
- `browser_result`: Final navigation URL, page title, and observation summaries.
- `evaluation`: Verdict score, evaluation rule results, and safety compliance checks.
- `reliability`: Idempotency token, retry counters, and DLQ state.
- `video_artifact_id`: Storage artifact reference for full-session WebM video recordings.
- `trace_context`: `{"trace_id": "...", "span_id": "..."}` for distributed trace correlation.
- `priority_queue`: Kafka topic destination (`agent.tasks.high`, `queued`, `batch`).
- `self_healed`: Boolean indicating whether selector self-healing succeeded.
- `self_healing_events`: Detailed recovery records (`step_index`, `original_selector`, `healed_selector`, `strategy`, `confidence`).
- `aborted`: Boolean indicating if execution was halted via online cancellation.
- `aborted_by`: Identity of the actor who initiated the abort.

### Dead Letter Queue (DLQ) Metadata Example:
```json
{
  "reliability": {
    "dlq": {
      "status": "pending",
      "topic": "agent.tasks.dlq",
      "worker_id": "worker-local",
      "attempts": 2,
      "error": {
        "type": "RuntimeError",
        "message": "Target browser element unreachable"
      }
    },
    "replay": {
      "count": 1,
      "last_replayed_by": "operator@example.com"
    }
  }
}
```

---

## Task Steps Table (`task_steps`)

Maintains granular per-step execution outputs for Visual Step Replay:

```json
{
  "duration_ms": 124.5,
  "span_id": "e2a1b3c4d5f67890",
  "screenshot_artifact_id": "00000000-0000-0000-0000-000000000099",
  "dom_summary": "Dashboard Home (url: https://example.com/)",
  "error": null,
  "self_healed": true,
  "healing_details": {
    "original_selector": "button#submit-old",
    "healed_selector": "button[data-testid='submit-btn']",
    "strategy": "semantic_attribute",
    "confidence": 0.88
  }
}
```

---

## Artifact Governance Specification

The `ArtifactStore` handles multi-media payloads:
1. **Screenshot**: `media_type="screenshot"`, PNG format.
2. **HTML DOM Snapshot**: `media_type="html"`, raw HTML.
3. **WebM Video Recording**: `media_type="video"`, `video/webm` MIME type.
4. **Session Vault Credentials**: `media_type="storage_state"`, `application/json` encrypted storage state.

### Session Artifact Metadata (KMS Envelope Encryption):
```json
{
  "session_name": "portal_admin_session",
  "cookies_count": 5,
  "backend": "s3",
  "status": "valid",
  "encrypted": true,
  "kms_provider": "local",
  "key_id": "session-vault-v1",
  "algorithm": "AES-256-GCM",
  "aad_tenant_id": "00000000-0000-0000-0000-000000000001",
  "encrypted_dek": "b64_encrypted_data_encryption_key_==",
  "iv": "b64_initialization_vector_==",
  "tag": "b64_gcm_auth_tag_==",
  "ciphertext": "b64_aes_gcm_encrypted_payload_=="
}
```

---

## Standardized Audit Events

The `audit_logs` table records an append-only timeline of operational events:

| Event Type | Description |
| :--- | :--- |
| `task.created` | Automation task submitted. |
| `task.approved` | Task approved by an authorized approver. |
| `task.execution_started` | Worker acquired task lock and launched browser. |
| `task.artifact_written` | Screenshot, HTML, video, or session written to store. |
| `task.evaluated` | Automated safety and policy checks completed. |
| `task.completed` | Task successfully finished. |
| `task.self_healed` | Broken DOM selector recovered via heuristic cascade. |
| `task.aborted` | Task interrupted via online cancellation endpoint. |
| `task.paused` | Task suspended for Human-in-the-Loop takeover. |
| `task.interacted` | Mouse click, keyboard typing, or key press injected. |
| `task.resumed` | Automation loop resumed following human intervention. |
| `task.dlq_replayed` | Failed DLQ task requeued for execution. |
| `task.dlq_quarantined` | Poisoned task isolated from bulk retry flows. |
| `scheduled_task.created` | New Cron schedule registered. |
| `scheduled_task.triggered` | Cron dispatcher initiated recurring task run. |
| `session.revoked` | Browser credentials marked revoked in vault. |
| `session.validated` | KMS cryptographic round-trip verified session integrity. |
| `auth.oidc_callback_success` | OIDC Authorization Code Flow SSO completed successfully. |
| `federation.heartbeat` | Cluster node heartbeat registered. |
| `federation.re_elected` | Cluster scheduler leadership reassigned to standby node. |
| `alert.test_dispatched` | Outbound test notification sent to Slack/Discord webhook. |

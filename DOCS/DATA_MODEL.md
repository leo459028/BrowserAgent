# Data Model

資料模型以 [src/browser_agent/models.py](../src/browser_agent/models.py) 為準。V1.4 包含 Alembic migration `0004_v14_federation_and_matrix`，新增 `cluster_nodes` 資料表與 `tasks`（`browser_engine`, `matrix_id`, `human_intervened`, `dlp_masked`）擴充欄位，延續 V1.2 `0003_v12_scheduled_tasks` 之 `scheduled_tasks` 表與工作階段憑證保險箱。

## Local Dev Identity

`scripts/bootstrap.py` 會 seed 一組 local dev tenant/users：

| Role | Email | UUID |
|---|---|---|
| admin | `ops@example.com` | `00000000-0000-0000-0000-000000000002` |
| creator | `creator@example.com` | `00000000-0000-0000-0000-000000000003` |
| approver | `approver@example.com` | `00000000-0000-0000-0000-000000000004` |
| operator | `operator@example.com` | `00000000-0000-0000-0000-000000000005` |

Tenant：`00000000-0000-0000-0000-000000000001`。

## Tasks Table (`tasks`) V1.4 擴充欄位

| 欄位 | 型別 | 描述 |
|---|---|---|
| `browser_engine` | Text | 指定執行的瀏覽器核心：`chromium`（預設）、`firefox` 或 `webkit` |
| `matrix_id` | Text | 跨瀏覽器矩陣執行批次唯一識別碼（nullable，矩陣派發時自動賦值） |
| `human_intervened` | Boolean | 任務執行過程中是否曾由維運人員介入遠端操作（預設 `False`） |
| `dlp_masked` | Boolean | 任務執行期是否套用了 Zero-Trust 動態資料脫敏與像素遮罩（預設 `False`） |
| `scheduled_task_id` | UUID (FK) | 來源 Scheduled Task ID（若為定時巡檢產生） |

## Cluster Nodes Table (`cluster_nodes`)

V1.4 新增資料表，用於多叢集排程同盟拓撲與分散式租約狀態記錄：

| 欄位 | 型別 | 描述 |
|---|---|---|
| `id` | UUID (PK) | 節點唯一主鍵識別碼 |
| `node_id` | Text (Unique) | 叢集節點唯一名稱標識（如 `cluster-node-tokyo-01`） |
| `region` | Text | 所屬地理區域識別標籤（如 `ap-northeast-1`） |
| `status` | Text | 存活狀態：`online`、`degraded`、`offline` |
| `is_leader` | Boolean | 當前是否持有 Leader 排程租約主導權 |
| `active_schedules_count` | Integer | 當前指派至此節點或由其管理的活躍排程數 |
| `last_heartbeat` | DateTime (UTC) | 最後心跳時間戳記 |
| `metadata_` | JSON | 節點健康度、負載與環境 metadata |
| `created_at` | DateTime (UTC) | 節點首次註冊時間 |
| `updated_at` | DateTime (UTC) | 節點最後更新時間 |

## Scheduled Tasks Table (`scheduled_tasks`)

V1.2 新增資料表，用於支援定時巡檢任務排程調度：

| 欄位 | 型別 | 描述 |
|---|---|---|
| `id` | UUID (PK) | 排程唯一識別碼 |
| `tenant_id` | UUID (FK) | 所屬租戶 ID |
| `name` | Text | 排程名稱 |
| `cron_expression` | Text | 標準 5 欄位 Cron 表達式（分 時 日 月 週） |
| `concurrency_policy` | Text | 並行原則：`skip`（預設，跳過派發避免重複）或 `allow`（允許並行） |
| `is_active` | Boolean | 排程啟用開關，預設 `True` |
| `task_template` | JSON | 觸發時所建立 Task 之預設定義模板（title, instructions, risk_level 等） |
| `last_run_at` | DateTime (UTC) | 上次觸發派發時間 |
| `next_run_at` | DateTime (UTC) | 預計下次觸發時間 |
| `created_by` | UUID (FK) | 建立者 User ID |
| `created_at` | DateTime (UTC) | 建立時間戳記 |
| `updated_at` | DateTime (UTC) | 最後更新時間戳記 |

## Task Metadata

`tasks.metadata` 會包含：

- `policy`：policy decision 與 reason。
- `planner`：Planner version、validation、fallback、SkillHub resolution。
- `plan`：browser action plan 與 resolved skill metadata。
- `browser_result`：final URL、title、observations。
- `evaluation`：score、verdict、checks。
- `reliability`：idempotency、DLQ、replay、quarantine metadata。
- `video_artifact_id`：全行程 WebM 錄影視訊 Artifact ID。
- `trace_context`：`{"trace_id": "...", "span_id": "..."}`。
- `priority_queue`：發布之 Kafka 主題（`agent.tasks.high`、`agent.tasks.queued` 或 `agent.tasks.batch`）。
- `self_healed`：是否觸發並成功執行選擇器自我修復（`true`/`false`）。
- `self_healing_events`：自癒詳細歷程清單（含 step_index、original_selector、healed_selector、strategy、confidence）。
- `aborted`：任務是否遭到線上即時中止（`true`/`false`）。
- `aborted_by`：執行中斷的使用者帳號或 Actor ID。

DLQ metadata 範例：

```json
{
  "reliability": {
    "dlq": {
      "status": "pending",
      "topic": "agent.tasks.dlq",
      "worker_id": "worker-local",
      "attempts": 2,
      "error": {"type": "RuntimeError", "message": "browser crashed"}
    },
    "replay": {
      "count": 1,
      "last_replayed_by": "operator@example.com"
    }
  }
}
```

Quarantine 後 `dlq.status` 會變成 `quarantined`，並新增 `dlq.quarantine.reason`、`quarantined_at`、`quarantined_by`。

## Task Steps

Worker 執行後會更新 `task_steps.status` 與 `task_steps.output_data`。`output_data` 記錄視覺化步驟回放資訊：

```json
{
  "duration_ms": 124.5,
  "span_id": "e2a1b3c4d5f67890",
  "screenshot_artifact_id": "00000000-0000-0000-0000-000000000099",
  "dom_summary": "Example Domain (url: https://example.com/)",
  "error": null,
  "self_healed": true,
  "healing_details": {
    "original_selector": "button#login-btn-old",
    "healed_selector": "button[data-testid='login-submit']",
    "strategy": "semantic_attribute",
    "confidence": 0.85
  }
}
```

## Artifacts Specification

ArtifactStore 支援多種媒體型別（Media Types）：

1. **Screenshot**：`media_type="screenshot"`，PNG 格式。
2. **HTML DOM Snapshot**：`media_type="html"`，HTML 格式。
3. **WebM Video Recording**：`media_type="video"`，MIME 為 `video/webm`，全行程瀏覽器螢幕視訊。
4. **Session Vault (Storage State)**：`media_type="storage_state"`，MIME 為 `application/json`。內含 Playwright cookies 與 localStorage 狀態。

Session Artifact Metadata 規格（支援 KMS 信封加密）：
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

S3 artifact metadata 範例：

```json
{
  "backend": "s3",
  "bucket": "browser-agent",
  "key": "2026/05/22/<task-id>/video-abc.webm",
  "content_type": "video/webm",
  "size_bytes": 543210,
  "retention": {"policy": "default", "expires_at": null},
  "redaction": {"status": "not_applied", "strategy": "noop"}
}
```

## Audit Events

常規與維運 events：

- `task.created`
- `task.approved`
- `task.dlq_replayed`
- `task.dlq_quarantined`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`
- `task.self_healed`（選擇器自我修復成功事件）
- `task.aborted`（線上即時中斷事件）
- `alert.test_dispatched`（手動測試派發 Webhook 告警紀錄）
- `scheduled_task.created`
- `scheduled_task.updated`
- `scheduled_task.deleted`
- `scheduled_task.triggered`
- `session.revoked`
- `session.validated`（KMS 解密驗證事件）
- `auth.oidc_callback_success`（OIDC SSO 授權回調成功）
- `otlp.flushed`
- `task.paused`（雙向遠端接管進入暫停事件）
- `task.resumed`（雙向遠端接管恢復自動化推進事件）
- `task.interacted`（下發反向操作指令注入事件）
- `federation.heartbeat`（多叢集節點心跳註冊事件）
- `federation.re_elected`（同盟領導權強制重選事件）

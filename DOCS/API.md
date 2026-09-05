# API

Base URL：

```text
http://localhost:8000
```

V1.1 預設啟用 Auth/RBAC。除了 `/healthz`、`/readyz`、`/operations` 與 local dev token endpoint 之外，API 需要：

```text
Authorization: Bearer <JWT>
```

## Auth

### `POST /v1/auth/local-token`

本機開發與 Operations Center 使用的 token endpoint。只有 `AUTH_LOCAL_TOKENS_ENABLED=true` 時啟用。

Request：

```json
{"role": "operator"}
```

可用 role：`creator`、`approver`、`operator`、`admin`。

### `GET /v1/auth/me`

回傳目前 token actor 與 permissions。`AUTH_MODE=local` 使用 HS256 local dev token；`AUTH_MODE=jwks` 使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token。若沒有設定 `AUTH_JWKS_URL`，但有 `AUTH_OIDC_ISSUER_URL`，會讀取 OIDC discovery 的 `jwks_uri`。支援從 `Authorization: Bearer <token>` 或 HttpOnly `ba_session` Cookie 認證。

### `GET /v1/auth/oidc/login`

公開端點。發起 Enterprise OIDC Authorization Code Flow SSO 登入流程：
- 自動生成高強度隨機 PKCE `code_verifier` 與 SHA-256 `code_challenge`。
- 自動生成防偽 `state`，並將 PKCE 憑證暫存於後端快取。
- 回傳 HTTP 307 臨時重新導向至外部 IdP 授權端點（`AUTH_OIDC_ISSUER_URL/protocol/openid-connect/auth`）。

### `GET /v1/auth/oidc/callback`

公開端點。接收 IdP 授權重定向回傳之 `code` 與 `state`：
- 校驗 `state` 防範跨站請求偽造（CSRF）。
- 檢索對應的 `code_verifier`，向 IdP Token 端點以 PKCE 交換 `id_token` 與 `access_token`。
- 驗證 JWT 簽名與 Claim，登入成功後簽發 HttpOnly、SameSite 嚴格模式之安全 Cookie（`ba_session`）。
- 寫入 `auth.oidc_callback_success` 審計日誌，並重定向回 `/operations`。

## Operations

### `GET /operations`

回傳 `Browser Agent Operations Center`（V1.3）。可用來建立 task、核准、查 Operations Readiness、Production Readiness、Observability、Production Alerting、Trace Inspector、Visual Step Replay、Live Stream 即時畫面、Session Vault、KMS 信封加密狀態、優先佇列監控、Reliability/DLQ、bulk replay、quarantine、metrics、audit、Planner/SkillHub、artifact preview/access。

系統支援自動容錯重定向：
- `GET /` ➜ 307 臨時重定向至 `/operations`
- `GET /operation` ➜ 307 臨時重定向至 `/operations`

### `GET /v1/ops/readiness`

需要 `operator` 或 `admin`。回傳 app version、auth mode、local token 狀態、DB readiness、reliability store、Kafka config、artifact backend、worker identity、DLQ topic、Production Readiness、Observability 與 warnings。

包含欄位：

- `production.status`：`ready`、`degraded` 或 `not_ready`。
- `production.checks`：檢查 production local token、secret key、JWKS/OIDC、Redis reliability、Kafka、S3 artifact backend。
- `observability.otel_ready`：表示目前 log/request schema 已預留 OTEL 欄位。
- `observability.log_schema_fields`：列出固定 log correlation 欄位。
- `kubernetes`：包含 `in_cluster`（是否運行於 K8s Pod 內）與 `manifests_available`（是否存在 `deploy/k8s/`）。
- `otlp`：包含 `enabled`、`endpoint`、`queue_size`、`dropped_spans`、`exported_spans`。

Production hard failure 會讓整體 `status` 回 `not_ready`。

### `GET /v1/ops/kms/status`

需要 `operator` 或 `admin`。查詢 Session Vault 企業級 KMS 信封加密引擎的運行狀態與健康指標：
- `status`：`healthy` 或 `degraded`。
- `provider`：當前驅動類型（`local`、`aws_kms`、`vault`）。
- `key_id`：使用中之主金鑰識別碼（例如 `session-vault-v1`）。
- `algorithm`：`AES-256-GCM`。
- `test_encryption`：`{"ok": true, "roundtrip_ms": float}` 即時加解密迴路驗證。

### `GET /v1/ops/queues`

需要 `operator` 或 `admin`。查詢多優先權加權佇列（High / Queued / Batch）與 Worker 資源池隔離分流狀態：
- `queues`：各優先等級主題（`agent.tasks.high`, `agent.tasks.queued`, `agent.tasks.batch`）之即時深度與優先權定義。
- `worker_pool`：當前 Worker 資源池名稱（`default`, `high-priority`, `batch-pool`）及其訂閱之主題清單。
- `metrics`：包含 `high_priority_routed`、`normal_priority_routed`、`batch_priority_routed`。

### `GET /v1/ops/alerts`

需要 `operator` 或 `admin`。即時評估維運系統的 7 大規則，回傳系統整體健康指標與觸發之告警清單：
- `evaluation_time`：評估時間（ISO 8601）。
- `summary`：`{"critical": int, "warning": int, "info": int, "healthy": bool}`。
- `metrics_snapshot`：包含 failure rate、DLQ backlog、pending approval 數量、Worker 心跳、DB 延遲等即時數值。
- `alerts`：觸發之告警項目（含 rule_id、severity、message、metric_name、metric_value、threshold、recommendation）。
- `webhook_enabled`：外部 Webhook（Slack/Discord）是否已設定。

### `POST /v1/ops/alerts/test-dispatch`

需要 `admin`。手動測試外部 Webhook 轉發通道，發送測試告警至 Slack/Discord 或外部 Webhook URL，並記錄 Audit log。
Request body：
```json
{
  "rule_id": "test_alert",
  "severity": "info",
  "message": "Manual test notification from operations center"
}
```

### `GET /v1/ops/traces/{trace_id}`

需要 `operator` 或 `admin`。檢視指定 `trace_id` 的端到端分散式追蹤圖。聚合 API 與 Worker 記憶體中的 TraceBuffer 與資料庫儲存的 Task Steps，回傳：
- `trace_id`：32-char hex trace identifier。
- `span_count`：關聯之 Span 總數。
- `root_service`：進入點服務。
- `spans`：階層式 Spans 列表（包含 span_id、parent_span_id、name、service_name、start_time、end_time、duration_ms、status、attributes、events）。

### `GET /v1/ops/otlp/status`

需要 `operator` 或 `admin`。查詢 OpenTelemetry OTLP Batch Span Exporter 的運行狀態，回傳：
- `enabled`：是否啟用 OTLP 導出。
- `endpoint`：OTLP HTTP 接收端點。
- `queue_size`：當前記憶體隊列積壓數。
- `max_queue_size`：隊列容量上限。
- `exported_spans`：成功推送之 Span 累計總數。
- `dropped_spans`：因隊列滿載或推送失敗丟棄之 Span 數。
- `batch_size`：單次推播批次大小。

### `POST /v1/ops/otlp/flush`

需要 `admin`。手動強制排空當前佇列中積壓的 Spans，立即向外部 OTLP 端點推送。

## Health 與 Metrics

- `GET /healthz`：公開 health。
- `GET /readyz`：公開 database readiness。
- `GET /metrics`：需要 `operator` 或 `admin`。

V1.2 每個 response 會回寫 `X-Correlation-ID`。若 request 帶入 `X-Correlation-ID`，會沿用；未帶入時由 API 產生。API 也會解析 W3C `traceparent`，在 API 與 Worker 間傳遞分佈式追蹤 Context。

## Tasks

### `POST /v1/tasks`

需要 `creator` 或 `admin`。支援 `Idempotency-Key`。同 tenant 同 key 同 payload 回既有 task；同 key 不同 payload 回 `409`。

### `GET /v1/tasks`

需要 authenticated actor。回傳同 tenant recent tasks。

### `GET /v1/tasks/{task_id}`

需要 authenticated actor。只允許讀同 tenant task。

### `POST /v1/tasks/{task_id}/approve`

需要 `approver` 或 `admin`。核准 `pending_approval` task，狀態轉為 `queued`，並發布 `agent.tasks.queued`。

### `GET /v1/tasks/{task_id}/audit`

需要 `approver`、`operator` 或 `admin`。回傳 task audit timeline。

### `GET /v1/tasks/{task_id}/replay`

需要 `approver`、`operator` 或 `admin`。回傳可視化步驟回放（Visual Step Replay）與 WebM 視訊串流資訊，100% 向後相容：
- `task_id`：任務 ID。
- `trace_id`：此任務綁定之分散式追蹤 Trace ID。
- `video_artifact_id`：全行程錄製之 WebM 視訊 Artifact ID（若有錄影）。
- `video_url`：WebM 視訊即時串流端點網址（`/v1/tasks/{task_id}/video`）。
- `steps_visual`：步驟視覺化列表，包含 `step_index`、`step_type`、`status`、`duration_ms`、`span_id`、`screenshot_artifact_id`、`dom_summary`。
- `evaluation_summary`：步驟執行摘要評估。
- `timeline`：由 audit、steps、artifacts 組成之向後相容事件時間線。

### `GET /v1/tasks/{task_id}/video`

需要 authenticated actor。取得該任務全行程瀏覽器 WebM 錄影視訊串流，以 `video/webm` 二進位串流回傳，支援串流播放。

### `WS /v1/tasks/{task_id}/live-stream`

需要 authenticated actor。提供即時雙向/單向低延遲瀏覽器畫面廣播 WebSocket 串流：
- 連線建立後，系統以設定之幀率（預設 2 FPS）非同步推送當前瀏覽器視窗最新 JPEG 畫面幀（Base64 編碼），格式為 `{"type": "frame", "frame_id": int, "timestamp": str, "data": "data:image/jpeg;base64,..."}`。
- 當任務步驟轉換或自癒發生時，推播事件通知 `{"type": "event", "event": "step_started", ...}`。
- 支援客戶端發送 `ping` 保活，伺服器回傳 `pong`。
- 任務結束或中斷時，推播 `{"type": "task_finished", "status": "completed|failed|aborted"}` 並優雅關閉連線。

### `POST /v1/tasks/{task_id}/abort`

需要 `operator` 或 `admin`。即時線上中止執行中之任務：
- 即刻標記任務 Abort 信號，Worker 瀏覽器執行迴圈於下一步驟前偵測並立即中斷。
- 安全關閉 Playwright Page 與 Context 資源，避免孤兒行程或記憶體洩漏。
- 任務狀態躍遷為 `aborted`，寫入 `task.aborted` 審計日誌與 Evaluation 判定。
- 回傳：
```json
{
  "aborted": true,
  "task_id": "00000000-0000-0000-0000-000000000201",
  "status": "aborted",
  "aborted_by": "operator@example.com"
}
```

## Scheduled Tasks（排程調度引擎）

### `POST /v1/scheduled-tasks`

需要 `creator` 或 `admin`。建立定時巡檢排程：
```json
{
  "name": "Daily Portal Health Check",
  "cron_expression": "0 9 * * *",
  "concurrency_policy": "skip",
  "is_active": true,
  "task_template": {
    "title": "Portal Inspection",
    "instructions": "Navigate to portal and check dashboard status.",
    "risk_level": "low",
    "metadata": {"start_url": "https://portal.internal", "domains": ["portal.internal"]}
  }
}
```

### `GET /v1/scheduled-tasks`

需要 `operator` 或 `admin`。列出同租戶的所有定時巡檢排程清單，包含各排程之 `id`、`name`、`cron_expression`、`concurrency_policy`、`is_active`、`task_template`、`last_run_at`、`next_run_at` 與 `created_at`。

### `PATCH /v1/scheduled-tasks/{schedule_id}`

需要 `creator` 或 `admin`。更新指定排程之可選屬性：
```json
{
  "name": "Updated Schedule Name",
  "cron_expression": "*/30 * * * *",
  "concurrency_policy": "allow",
  "is_active": false,
  "task_template": {
    "title": "Updated Task Template"
  }
}
```
可藉由設定 `is_active: false` 暫停或停用該排程。

### `POST /v1/scheduled-tasks/{schedule_id}/run`

需要 `creator`、`operator` 或 `admin`。手動立即觸發派發該排程任務（不受 Cron 時間限制，但仍遵循並行鎖與 Policy 保護）：
```json
{
  "triggered": true,
  "scheduled_task_id": "00000000-0000-0000-0000-000000000101",
  "task_id": "00000000-0000-0000-0000-000000000202",
  "status": "queued"
}
```

### `POST /v1/scheduled-tasks/evaluate`

需要 `operator` 或 `admin`。手動觸發執行全體定時排程之掃描與到期評估（Worker 進程亦會在背景定期自動評估）。

## Session Vault（工作階段治理）

### `GET /v1/sessions`

需要 `operator` 或 `admin`。列出目前租戶下所有已封裝之 `storage_state` 憑證工作階段 Artifacts，回傳陣列包含：
```json
[
  {
    "session_name": "portal_admin_session",
    "artifact_id": "00000000-0000-0000-0000-000000000301",
    "task_id": "00000000-0000-0000-0000-000000000201",
    "cookies_count": 5,
    "created_at": "2026-09-05T08:00:00Z",
    "uri": "s3://browser-agent/2026/09/05/.../storage_state.json",
    "backend": "s3",
    "status": "valid",
    "encrypted": true,
    "kms_provider": "local",
    "key_id": "session-vault-v1"
  }
]
```

### `GET /v1/sessions/{session_name}/validate`

需要 `operator` 或 `admin`。完整性檢驗指定 `session_name` 之最新憑證：
- 透過 KMS 引擎即時執行解密迴路，校驗 AES-256-GCM 標籤與租戶 AAD。
- 解析 JSON Payload 並統計 Cookies 與 LocalStorage 鍵值數。
- 回傳：
```json
{
  "session_name": "portal_admin_session",
  "valid": true,
  "encrypted": true,
  "kms_provider": "local",
  "cookies_count": 5,
  "origins_count": 1,
  "status": "valid"
}
```

### `DELETE /v1/sessions/{session_name}`

需要 `admin`。強制撤銷指定 `session_name` 之所有登入工作階段憑證，標記其狀態為 `revoked`，防止後續任務自動重用：
```json
{
  "revoked": true,
  "session_name": "portal_admin_session",
  "count": 1
}
```

## Reliability / DLQ

- `GET /v1/reliability`：operator/admin 查 reliability settings。
- `GET /v1/dlq/tasks`：operator/admin 查 failed DLQ tasks。
- `POST /v1/dlq/tasks/{task_id}/replay`：單筆 replay。
- `POST /v1/dlq/tasks/bulk-replay`：批次 replay，body 包含 `task_ids` 與 optional `note`。
- `POST /v1/dlq/tasks/{task_id}/quarantine`：標記 poison task，bulk replay 會跳過 quarantined task。

## Artifacts

### `GET /v1/artifacts/{artifact_id}/content`

需要 authenticated actor。支援 local filesystem 與 `s3://bucket/key` artifact。Access checks：

- artifact 必須存在。
- artifact 所屬 task tenant 必須符合 token tenant。
- local artifact path 必須在 `ARTIFACT_BASE_PATH` 之內。

## Skills

- `POST /v1/skills`：需要 `admin`，註冊同 tenant SkillHub capability。
- `GET /v1/skills`：需要 authenticated actor，列出同 tenant skills。

## V1.4 雙向即時遠端接管（HITL Reverse Control Channel）

### `POST /v1/tasks/{task_id}/pause`

需要 `operator` 或 `admin`。線上暫停執行中之任務，切換進入 HITL（Human-in-the-Loop）人機協作模式。Worker 收到中斷請求後將懸掛自動化推進迴圈，等待人工操作。

Request Body：
```json
{
  "reason": "Solve cloudflare CAPTCHA"
}
```

Response：
```json
{
  "task_id": "d2b545c0-3431-4518-99ab-e703c36d66fc",
  "paused": true,
  "operator": "operator@example.com",
  "reason": "Solve cloudflare CAPTCHA"
}
```

### `POST /v1/tasks/{task_id}/interact`

需要 `operator` 或 `admin`。下發遠端人機操作指令至執行中的瀏覽器實體。目前支援 `click`、`type`、`press` 三種動作。

Request Body (點擊)：
```json
{
  "action": "click",
  "x": 350.5,
  "y": 210.0
}
```

Request Body (文字輸入)：
```json
{
  "action": "type",
  "text": "my_secure_code_123"
}
```

Request Body (鍵盤按鍵)：
```json
{
  "action": "press",
  "key": "Enter"
}
```

Response：
```json
{
  "task_id": "d2b545c0-3431-4518-99ab-e703c36d66fc",
  "queued": true,
  "action": "click",
  "operator": "operator@example.com"
}
```

### `POST /v1/tasks/{task_id}/resume`

需要 `operator` 或 `admin`。恢復暫停之任務，讓瀏覽器自動化繼續推進，並於審計歷程與任務狀態中標記 `human_intervened = true`，記錄介入耗時與操作者帳號。

Response：
```json
{
  "task_id": "d2b545c0-3431-4518-99ab-e703c36d66fc",
  "resumed": true,
  "operator": "operator@example.com"
}
```

## V1.4 跨瀏覽器矩陣執行引擎（Cross-Browser Matrix Execution）

### `POST /v1/tasks/matrix`

需要 `creator` 或 `admin`。一鍵建立並派發一組跨瀏覽器核心的平行任務，自動為每個指定核心生成專屬 Task，並共享相同之 `matrix_id`。

Request Body：
```json
{
  "title": "Checkout Flow Cross-Browser Test",
  "instructions": "Navigate to checkout, fill form, verify total price",
  "priority": 1,
  "risk_level": "low",
  "engines": ["chromium", "firefox", "webkit"],
  "metadata": {
    "start_url": "https://example.com/checkout"
  }
}
```

Response：
```json
{
  "matrix_id": "matrix-9c3f2e1a4b8d",
  "total_tasks": 3,
  "tasks": [
    {
      "task_id": "acb1ceb5-84b6-4ecf-bdcf-9c0c3d547956",
      "browser_engine": "chromium",
      "status": "pending_approval",
      "title": "[Chromium] Checkout Flow Cross-Browser Test"
    },
    {
      "task_id": "2893b283-9402-4d41-84c4-a8bb4499221d",
      "browser_engine": "firefox",
      "status": "pending_approval",
      "title": "[Firefox] Checkout Flow Cross-Browser Test"
    },
    {
      "task_id": "3655d0c8-5308-4ec0-a1a7-90dd7607e6be",
      "browser_engine": "webkit",
      "status": "pending_approval",
      "title": "[Webkit] Checkout Flow Cross-Browser Test"
    }
  ]
}
```

### `GET /v1/tasks/matrix/{matrix_id}`

需要 authenticated actor。查詢指定矩陣批次中所有瀏覽器任務之聚合狀態、執行結果、耗時與差異化截圖。

Response：
```json
{
  "matrix_id": "matrix-9c3f2e1a4b8d",
  "tasks": [
    {
      "task_id": "acb1ceb5-84b6-4ecf-bdcf-9c0c3d547956",
      "browser_engine": "chromium",
      "status": "completed",
      "title": "[Chromium] Checkout Flow Cross-Browser Test",
      "verdict": "pass",
      "score": 100,
      "self_healed": false,
      "dlp_masked": true,
      "human_intervened": false,
      "video_artifact_id": "uuid-video-1",
      "created_at": "2026-09-05T08:00:00Z",
      "completed_at": "2026-09-05T08:00:15Z"
    },
    {
      "task_id": "2893b283-9402-4d41-84c4-a8bb4499221d",
      "browser_engine": "firefox",
      "status": "completed",
      "title": "[Firefox] Checkout Flow Cross-Browser Test",
      "verdict": "pass",
      "score": 98,
      "self_healed": true,
      "dlp_masked": true,
      "human_intervened": false,
      "video_artifact_id": "uuid-video-2",
      "created_at": "2026-09-05T08:00:00Z",
      "completed_at": "2026-09-05T08:00:18Z"
    },
    {
      "task_id": "3655d0c8-5308-4ec0-a1a7-90dd7607e6be",
      "browser_engine": "webkit",
      "status": "completed",
      "title": "[Webkit] Checkout Flow Cross-Browser Test",
      "verdict": "pass",
      "score": 95,
      "self_healed": false,
      "dlp_masked": true,
      "human_intervened": true,
      "video_artifact_id": "uuid-video-3",
      "created_at": "2026-09-05T08:00:00Z",
      "completed_at": "2026-09-05T08:00:25Z"
    }
  ]
}
```

## V1.4 Zero-Trust 動態資料防洩保護（Zero-Trust Dynamic DLP）

### `GET /v1/ops/dlp/status`

需要 `operator` 或 `admin`。查詢當前 Zero-Trust DLP 防護服務狀態與作用中之資料脫敏與像素遮罩規則清單。

Response：
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

## V1.4 多叢集排程同盟與容災接管（Multi-Cluster Scheduling Federation）

### `GET /v1/ops/federation/nodes`

需要 `operator` 或 `admin`。檢視目前同盟叢集拓撲、各節點存活狀態（healthy / degraded / offline）、心跳時間戳與主導排程節點（Leader）。

Response：
```json
{
  "cluster_status": "healthy",
  "leader_node_id": "cluster-node-tokyo-01",
  "nodes": [
    {
      "node_id": "cluster-node-tokyo-01",
      "region": "ap-northeast-1",
      "status": "online",
      "is_leader": true,
      "active_schedules_count": 8,
      "last_heartbeat": 1757064000.5,
      "seconds_since_heartbeat": 1.2
    },
    {
      "node_id": "cluster-node-osaka-02",
      "region": "ap-northeast-3",
      "status": "online",
      "is_leader": false,
      "active_schedules_count": 0,
      "last_heartbeat": 1757064001.0,
      "seconds_since_heartbeat": 0.7
    }
  ]
}
```

### `POST /v1/ops/federation/heartbeat`

由排程節點或背景調度器定期（預設每 5 秒）調用，向同盟註冊中心發送心跳並回報活躍排程數。

Request Body：
```json
{
  "node_id": "cluster-node-tokyo-01",
  "region": "ap-northeast-1",
  "active_schedules_count": 8,
  "metadata": {"cpu_usage": 0.25, "memory_usage": 0.42}
}
```

Response：
```json
{
  "node_id": "cluster-node-tokyo-01",
  "registered": true,
  "is_leader": true
}
```

### `POST /v1/ops/federation/re-election`

需要 `admin` 角色。強制轉移同盟領導權，將 Leader 角色重派至指定備援節點，用於演練維護或跨區域容災接管。

Request Body：
```json
{
  "target_node_id": "cluster-node-osaka-02"
}
```

Response：
```json
{
  "re_elected": true,
  "leader_node_id": "cluster-node-osaka-02",
  "actor": "admin@example.com"
}
```

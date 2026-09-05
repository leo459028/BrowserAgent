# Security And Policy

## Auth/RBAC

V1.1 支援兩種 auth mode：

- `AUTH_MODE=local`：使用 `/v1/auth/local-token` 產生 local dev HS256 token。
- `AUTH_MODE=jwks`：使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token；若未設定 `AUTH_JWKS_URL`，可用 `AUTH_OIDC_ISSUER_URL` discovery 取得 `jwks_uri`。

Roles：

- `creator`：建立 task、讀 task/artifact。
- `approver`：讀 task/audit/artifact、approve task。
- `operator`：讀 task/audit/artifact/metrics、readiness、alerts、traces、DLQ operations。
- `admin`：全部權限（含 alerts test-dispatch、Skill 註冊等敏感操作）。

## Policy

Task create 仍會檢查 allowlist domains、risk level、sensitive instruction 與 prompt-injection pattern。Non-allowlisted domain 會 blocked；需要人工審核的 task 進入 `pending_approval`。

## Alerts & Tracing Controls

- 告警中心查詢 `GET /v1/ops/alerts` 與追蹤查詢 `GET /v1/ops/traces/{trace_id}` 僅限 `operator` 與 `admin`。
- 外部告警測試派發 `POST /v1/ops/alerts/test-dispatch` 僅限 `admin` 角色，且每次呼叫皆強制寫入 `alert.test_dispatched` 審計日誌，避免 Webhook 遭濫用。
- 外部 Webhook 發送採非阻塞背景執行緒與超時限制（預設 3 秒），防止第三方外部服務連線異常阻斷 API 或 Worker 主進程。
- 分散式追蹤 Span Attributes 與 TraceBuffer 不記錄使用者密碼、Token 或機密 Authorization Headers。
- OTLP Exporter 非同步推送僅導出結構化 Spans，提供隊列保護與錯誤丟棄機制，不阻斷業務流程。

## Scheduled Tasks Security

- 定時排程建立與屬性修改（`POST /v1/scheduled-tasks` 與 `PATCH /v1/scheduled-tasks/{schedule_id}`）僅限 `creator` 或 `admin` 角色。
- 定時排程停用可透過 `PATCH /v1/scheduled-tasks/{schedule_id}` 將 `is_active` 設為 `false`。
- 手動立即觸發排程（`POST /v1/scheduled-tasks/{schedule_id}/run`）支援 `creator`、`operator` 或 `admin`；手動評估排程（`POST /v1/scheduled-tasks/evaluate`）僅限 `operator` 或 `admin`。
- 排程派發任務必須經過相同的 Policy Engine 與網域白名單（Allowlist Domains）檢查，嚴防透過排程繞過安全性防護。

## Session Vault Security & Credential Governance

- Session Vault 保存之 Playwright `storage_state` 包含真實網站之 Cookies 與登入狀態（localStorage），屬於高敏感資產。
- 嚴格落實**多租戶隔離**：Worker 僅會在同一 `tenant_id` 下檢索與復用工作階段，跨租戶存取一律拒絕。
- 工作階段查詢（`GET /v1/sessions`）僅限 `operator` 與 `admin`。
- 工作階段強制撤銷（`DELETE /v1/sessions/{session_name}`）強制需要 `admin` 角色，並自動寫入 `session.revoked` 審計日誌。一旦標記為已撤銷，所有 Worker 立即停止重用該憑證。

## Video Recording Governance

- WebM 全行程錄影包含瀏覽器完整渲染與動態畫面。
- 視訊串流端點 `GET /v1/tasks/{task_id}/video` 強制校驗 Bearer Token 與租戶歸屬，嚴防未經授權之第三方存取。
- 視訊資料依據 Artifact 儲存後端保留政策管理，支援 S3 Lifecycle 自動清理過期視訊。

## Artifact Access

Artifact content endpoint 必須通過 tenant check。Local backend 會檢查 path 在 `ARTIFACT_BASE_PATH` 內；S3 backend 只讀 artifact metadata 指向的 `s3://bucket/key`。

## DLQ Controls

- DLQ list、single replay、bulk replay、quarantine 只允許 operator/admin。
- Bulk replay 會跳過 quarantined tasks。
- Quarantine 會寫入 `task.dlq_quarantined` audit。

## Production Notes

- Production 不應使用預設 `APP_SECRET_KEY`。
- Production 若仍開啟 local dev token，`/v1/ops/readiness` 會回 `not_ready`。
- Production 若使用預設 `APP_SECRET_KEY`、未設定 JWKS/OIDC、未設定 Kafka、未使用 Redis reliability store 或未使用 S3 artifact backend，`/v1/ops/readiness` 也會回 `not_ready`。
- JWKS/OIDC verifier 不等於完整 login flow；前端第三方登入導頁仍屬後續版本。
- V1.2 已內建正式 OpenTelemetry OTLP Exporter，可將跨進程 Traces 串流推送至外部 APM（如 Jaeger、Tempo、Datadog）。
- 部署於 Kubernetes 時，建議將敏感參數（如密鑰、S3 憑證、DB 密碼）抽離至 Kubernetes Secrets，並透過 KMS 加密。

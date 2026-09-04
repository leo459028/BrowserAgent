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
- JWKS/OIDC verifier 不等於完整 login flow；登入、session 與 IdP onboarding 仍屬後續版本。
- V1.1 內建輕量記憶體 TraceBuffer 與 W3C Context 傳播，生產環境若需跨節點持久化 Trace，後續版本將提供正式 OpenTelemetry OTLP Exporter。

# Security And Policy

## Auth/RBAC

V1.3 支援多元且嚴密的企業級認證模式：

- `AUTH_MODE=local`：使用 `/v1/auth/local-token` 產生 local dev HS256 token（僅限本機開發與測試）。
- `AUTH_MODE=jwks`：使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token；若未設定 `AUTH_JWKS_URL`，可用 `AUTH_OIDC_ISSUER_URL` discovery 取得 `jwks_uri`。
- `Enterprise OIDC SSO Code Flow`：
  - 標準 OAuth 2.0 / OpenID Connect Authorization Code Flow 搭配 **PKCE（RFC 7636）**。
  - 使用高熵隨機 `code_verifier` 與 SHA-256 `code_challenge`，杜絕授權碼攔截攻擊。
  - 隨機生成防偽 `state`，有效防範跨站請求偽造（CSRF）。
  - 授權成功後簽發之會話封裝於 **HttpOnly、SameSite 嚴格模式** 之安全 Cookie（`ba_session`），防範 XSS 竊取憑證。

Roles：

- `creator`：建立 task、讀 task/artifact、建立/修改 scheduled task。
- `approver`：讀 task/audit/artifact、approve task。
- `operator`：讀 task/audit/artifact/metrics、readiness、alerts、traces、DLQ operations、觸發排程、驗證 Session、線上中止任務（Abort）。
- `admin`：全部權限（含 alerts test-dispatch、Skill 註冊、一鍵強制撤銷 Session、排空 OTLP 等敏感操作）。

## Policy

Task create 仍會檢查 allowlist domains、risk level、sensitive instruction 與 prompt-injection pattern。Non-allowlisted domain 會 blocked；需要人工審核的 task 進入 `pending_approval`。

## Session Vault KMS 信封加密與憑證治理

- Session Vault 保存之 Playwright `storage_state` 包含真實網站之 Cookies 與登入狀態（localStorage），屬於頂級敏感憑證。
- **KMS 信封加密（Envelope Encryption）**：
  - 每次持久化前，系統由密碼學安全隨機產生獨立的 256-bit DEK（Data Encryption Key）。
  - 明文 DEK 使用 `AES-256-GCM` 驗證加密 Session 資料。
  - **強租戶隔離防篡改**：將 `tenant_id` 作為 AES-GCM 的 AAD（Additional Authenticated Data）綁定於密文中，若發生跨租戶非法調閱或密文置換，GCM 驗證直接拋出例外拒絕解密。
  - DEK 本身透過主金鑰（KMS Master Key，支援 Local、AWS KMS 或 HashiCorp Vault）加密保存。
  - 支援無痛金鑰輪換與 `/v1/sessions/{name}/validate` 即時解密迴路校驗。
- 工作階段查詢（`GET /v1/sessions`）僅限 `operator` 與 `admin`。
- 工作階段強制撤銷（`DELETE /v1/sessions/{session_name}`）強制需要 `admin` 角色，並自動寫入 `session.revoked` 審計日誌。一旦標記為已撤銷，所有 Worker 立即停止重用該憑證。

## 線上中斷與即時畫面串流安全（Abort & Live Stream Governance）

- 任務線上緊急中斷端點 `POST /v1/tasks/{task_id}/abort` 需 `operator` 或 `admin` 角色，中斷時安全關閉 Playwright Context 與 Page，避免資源洩漏與孤兒進程殘留，並寫入 `task.aborted` 審計日誌。
- WebSocket 即時畫面廣播端點 `WS /v1/tasks/{task_id}/live-stream` 強制校驗 Bearer Token 或 HttpOnly Cookie，且嚴格落實同租戶邊界隔離，杜絕跨租戶偷窺畫面。

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

## Video Recording Governance

- WebM 全行程錄影包含瀏覽器完整渲染與動態畫面。
- 視訊串流端點 `GET /v1/tasks/{task_id}/video` 強制校驗 Bearer Token 或 Cookie 與租戶歸屬，嚴防未經授權之第三方存取。
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
- V1.3 原生內建 Enterprise OIDC PKCE Code Flow 與 Session Vault KMS 信封加密，可直接對接企業級 IdP（Keycloak、Okta、Azure AD）與雲端金鑰管理服務（AWS KMS、HashiCorp Vault）。
- 部署於 Kubernetes 或 Helm 時，強烈建議將敏感參數（如密鑰、S3 憑證、DB 密碼）抽離至 Kubernetes Secrets，並透過雲端 KMS 加密。

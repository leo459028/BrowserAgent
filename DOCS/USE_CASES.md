# Use Cases

## Use Case：Operator 檢查 Operations Readiness

1. 取得 operator local dev token。
2. 開啟 `/operations`。
3. 查看 `Operations Readiness`。
4. 預期可看到 auth mode、artifact backend、warnings、worker identity、DLQ topic。

## Use Case：Production Readiness Smoke

1. 使用 `.env.production.example` 與 `docker-compose.prod.yml` 產生 Compose config。
2. 以 operator 或外部 IdP bearer token 呼叫 `GET /v1/ops/readiness`。
3. 查看 `production.status` 與 `production.checks`。
4. 預期 production-like 設定會關閉 local dev token、使用 JWKS/OIDC、Redis reliability、Kafka 與 S3 artifact backend。

## Use Case：OTEL-ready Correlation Smoke

1. 對任一 API request 帶入 `X-Correlation-ID`。
2. 可選擇帶入 W3C `traceparent`。
3. 預期 response 回寫同一個 `X-Correlation-ID`。
4. Log schema 中保留 `correlation_id`、`trace_id`、`parent_span_id`、`request_id`、`service_name`、`service_version` 與 `environment`。
5. V1.1 不會送 OTLP，也不代表完整 distributed tracing。

## Use Case：Normal Browser Task（人工建立、審查與步驟回放測試）

1. 在 `/operations` 左側 `Create Task` 卡片選擇 `Normal planner task`。
2. 點擊 `Create task`，任務建立並進入 `pending_approval` 狀態。
3. 左下方 Recent Tasks 點選該任務，右上角 **`Approve selected` 按鈕由灰轉綠（啟用）**。
4. 點擊 `Approve selected` 執行人工審核，任務轉為 `queued` ➜ `executing`。
5. Worker 執行完畢後任務狀態轉為 `completed`（右上角按鈕重回灰色鎖定）。
6. 右下角 `Visual Step Replay` 自動載入步驟分頁標籤（Step 1, Step 2）。點選特定步驟按鈕，即時預覽截圖縮圖、DOM 結構摘要與毫秒耗時。
7. 點選縮圖直接開啟全解析度截圖，展開折疊的 `▶ Raw Timeline Events` 檢驗完整 audit 與 lifecycle 事件。

## Use Case：S3 Artifact Governance

1. Docker Compose 設定 `ARTIFACT_BACKEND=s3`。
2. Task completed 後 artifacts 寫入 MinIO bucket。
3. Operations Center 顯示 artifact backend 為 `s3`。
4. Artifact content endpoint 使用 Bearer token 讀取 screenshot/html。
5. Tenant mismatch 仍回 `403`。

## Use Case：DLQ Bulk Replay

1. Operator 查 `GET /v1/dlq/tasks`。
2. 按 `Bulk DLQ replay` 或呼叫 `POST /v1/dlq/tasks/bulk-replay`。
3. Replayable tasks 回到 `queued`。
4. Quarantined tasks 出現在 skipped list。
5. Audit 寫入 `task.dlq_replayed`。

## Use Case：Quarantine Poison Task

1. Operator 對 failed DLQ task 呼叫 quarantine API。
2. `tasks.metadata.reliability.dlq.status` 變成 `quarantined`。
3. Bulk replay 不會重新排入該 task。
4. Audit 寫入 `task.dlq_quarantined`。

## Use Case：JWKS Auth Smoke

1. 設定 `AUTH_MODE=jwks`、`AUTH_JWKS_URL`、issuer、audience。
2. 用外部 IdP 或測試 JWKS 簽發 RS256 token。
3. 呼叫 `/v1/auth/me`。
4. 預期 valid token 回 actor；bad issuer/audience/expired/bad roles 回 `401`。

## Use Case：OIDC Discovery JWKS Smoke

1. 設定 `AUTH_MODE=jwks`、`AUTH_OIDC_ISSUER_URL`、issuer、audience，並留空 `AUTH_JWKS_URL`。
2. API 會讀取 `AUTH_OIDC_ISSUER_URL/.well-known/openid-configuration`。
3. 從 discovery response 的 `jwks_uri` 取得 JWKS。
4. 驗證 RS256 bearer token；缺少 `jwks_uri` 或 token 不合法時回 `401`。

## Use Case：生產告警中心與 Webhook 測試派發

1. Operator 或 Admin 登入 Operations Center。
2. 頂部儀表板顯示當前系統告警狀態徽章（如 `Healthy` 或 `Alerting`）。
3. 查閱 `Production Alerting Center`，檢視 7 大維運規則（DLQ、失敗率、待審核積壓、Worker 心跳、DB 延遲等）。
4. 點選 `Test Dispatch Webhook` 或以 Admin 呼叫 `POST /v1/ops/alerts/test-dispatch`。
5. 預期外部 Slack/Discord 通道收到非阻塞測試通知，系統寫入 `alert.test_dispatched` 審計日誌。

## Use Case：端到端分散式追蹤檢視（Trace Inspector）

1. 在 Operations Center 點選或複製任何任務之 `Trace ID`。
2. 貼入左側 `Trace Inspector` 輸入框，點擊 `Inspect Trace`。
3. 系統呼叫 `GET /v1/ops/traces/{trace_id}`，整合記憶體 TraceBuffer 與資料庫 Task Steps。
4. 預期展示樹狀 Span 清單：包含 HTTP Request、Kafka Publish、Worker Execution 以及各瀏覽器操作步驟（Span ID、耗時毫秒、狀態）。

## Use Case：視覺化步驟回放排查（Visual Step Replay）

1. 在 Operations Center 任務清單選取已完成或失敗之瀏覽器任務。
2. 右側 `Visual Step Replay` 面板自動載入步驟分頁條（Step 1、Step 2 等）。
3. 點選特定步驟按鈕，即時預覽該步驟之動作類型（navigate/screenshot/etc）、耗時（ms）、Span ID、DOM 結構摘要。
4. 若該步驟有截圖，自動顯示點選預覽縮圖，點擊可開啟完整解析度 Artifact，加速故障步驟定位。

## Use Case：Scheduled Tasks 定時巡檢排程調度

1. Operator 在 Operations Center 的 `Scheduled Tasks` 卡片建立定期巡檢任務，設定 Cron 表達式（例如每日早上 9:00 `0 9 * * *`）。
2. 設定任務負載（包含巡檢網站網址、操作步驟、低風險等級）。
3. 系統排程器背景搶取 Redis 分散式鎖，到達指定時間時自動派發全新 Task 進入流程。
4. 若配置 `concurrency_policy: skip`，當上一期巡檢仍在執行或待審核時，系統自動跳過本次派發，避免並發阻塞。
5. 維運人員可隨時點擊 `Run Now` 立即手動派發單次巡檢。

## Use Case：Session Vault 工作階段憑證治理與免登入復用

1. 登入任務完成後，Playwright 提取最新 Cookies 與 localStorage 狀態，以 `storage_state` 格式保存至 Session Vault。
2. 後續同網域與租戶之巡檢任務自動注入該工作階段，無需重複輸入帳密或觸發登入驗證。
3. Operations Center 的 `Session Vault` 卡片即時列出所有儲存的工作階段及其有效狀態與過期標記。

## Use Case：Session Vault 憑證外洩一鍵強制撤銷

1. 當安全性定期密碼輪換或偵測到憑證異常時，Admin 登入 Operations Center。
2. 在 `Session Vault` 列表找到該網域之 Session，點擊 `Revoke` 或呼叫 `DELETE /v1/sessions/{session_name}`。
3. 系統將該 Storage State 標記為 revoked，並寫入 `session.revoked` 審計日誌。
4. 後續任務將不再注入該憑證，強制重新執行完整登入驗證。

## Use Case：Full Video Replay 瀏覽器全行程 WebM 錄影播放

1. 建立任務時勾選啟用錄影（或系統預設啟用）。
2. Worker 在 Playwright 執行全程背景擷取畫面變化，並在任務完成後自動轉化為 WebM 視訊。
3. 視訊檔安全保存至 S3/Local ArtifactStore，並產生專屬串流 URL。
4. Operator 在 Operations Center 選取該任務時，右上側 Video 播放器自動載入視訊，可隨選播放、暫停與拖曳進度條，如同真實觀看工程師操作瀏覽器。

## Use Case：OpenTelemetry OTLP Exporter 串流推送至外部 APM

1. 維運人員配置 `OTEL_EXPORTER_OTLP_ENDPOINT`（如 Jaeger、Tempo 或 Datadog Agent 之 OTLP HTTP 端點）。
2. 系統在背景以非同步隊列批次收集所有 API 與 Worker 之 Span 呼叫鏈。
3. 累積至批次容量或超時時，自動以標準 OTLP JSON 協定推播至外部監控平台。
4. 呼叫 `GET /v1/ops/otlp/status` 或在 Operations Center 監控隊列深度與推播總數；支援 Admin `POST /v1/ops/otlp/flush` 強制立即排空推播。

## Use Case：Kubernetes 與 KEDA 自動擴展 Worker 資源池

1. 平台部署於 Kubernetes 叢集，套用 `deploy/k8s/` Kustomization。
2. KEDA ScaledObject 持續監聽 Kafka 佇列 `agent.tasks.queued` 之 consumer group lag。
3. 當大量定時巡檢同時觸發導致任務積壓時，KEDA 自動觸發 HPA 將 Worker Pod 副本數從 1 自動水平擴展至多達 10 個 Pod。
4. 任務排空後，Worker 叢集自動縮容至基準副本數，節省企業運算資源。

## Use Case：Enterprise OIDC SSO 一鍵登入與安全會話保持

1. 維運人員開啟 `/operations`，點選頂部 `SSO Login (OIDC)` 按鈕。
2. 瀏覽器發起 `GET /v1/auth/oidc/login`，攜帶 PKCE `code_challenge` 與隨機 `state` 導向企業 IdP（Keycloak/Okta）。
3. 使用者完成身份認證後，導回 `GET /v1/auth/oidc/callback`。
4. 系統交換授權碼並驗證簽名，自動寫入 HttpOnly、SameSite Strict 之 `ba_session` 安全 Cookie。
5. 維運人員無需在瀏覽器手動輸入或保管明文 Bearer Token，後續所有 UI 操作均自動由 Cookie 鑑權。

## Use Case：Session Vault KMS 信封加密與金鑰輪換完整性驗證

1. 登入任務產出的 Storage State 在寫入前，自動經由 KMS 信封加密（Local / AWS KMS / Vault）以 AES-256-GCM 加密，並以 `tenant_id` 作為 AAD 綁定。
2. 維運人員在 `Session Vault` 卡片點選 `Validate` 按鈕或呼叫 `GET /v1/sessions/{name}/validate`。
3. 系統即時執行解密迴路校驗，驗證 GCM 標籤完整性與金鑰匹配性，並回報有效 Cookies 數量。
4. 當安全政策要求更換主金鑰時，系統支援以新金鑰重新加密 DEK，舊有 Storage State 無需全部重新登入即可相容解密。

## Use Case：多優先權加權佇列分流與急件保障

1. 維運人員建立高風險線上突發告警排查任務，設定 `priority: 5`（急件）。
2. Orchestrator 自動將其路由至 `agent.tasks.high` 高優先權主題。
3. 專屬配置之 High-Priority Worker Pool 立即優先拉取並執行該急件任務，無需在預設佇列中排隊等待常規巡檢任務。
4. 呼叫 `GET /v1/ops/queues` 可隨時查看各佇列深度與路由統計。

## Use Case：瀏覽器即時畫面 WebSocket 廣播串流與線上緊急中斷（Abort）

1. 任務由 Worker 執行時，維運人員在 Operations Center 選取該任務。
2. 右側 `Live Telemetry Stream` 卡片透過 WebSocket（`WS /v1/tasks/{id}/live-stream`）即時以 2 FPS 渲染瀏覽器畫面。
3. 若維運人員觀察到頁面進入無限重試、第三方防爬蟲阻擋或非預期頁面，點選紅色的 **`Abort Task`** 按鈕。
4. API 呼叫 `POST /v1/tasks/{id}/abort`，Worker 在下一步驟執行前即時攔截中斷信號，安全關閉 Playwright 上下文並將任務標記為 `aborted`，防止資源浪費。

## Use Case：網頁改版啟發式選擇器自我修復（Heuristic Self-Healing）

1. 目標網站進行 UI 改版，按鈕的 ID 由 `button#submit-v1` 變更為 `button[data-testid='submit-v2']`。
2. Playwright 執行原選擇器發生找不到元素時，啟動 `HeuristicSelfHealingEngine`。
3. 自癒引擎掃描 DOM 樹，透過語意標籤與按鈕文字進行相似度比對（得分 > 0.6），成功推斷出新的候選選擇器並重新嘗試。
4. 動作成功完成，系統寫入 `task.self_healed` 審計日誌，在 Visual Step Replay 標記綠色 `Self-Healed ✓`，確保自動化管線在無人值守情況下依然強韌穩定。

## Use Case：Enterprise Helm 3 Chart 套件與 GitOps ArgoCD 持續交付

1. SRE 團隊使用 `deploy/helm/browser-agent/` 將 BrowserAgent 部署至 Kubernetes 叢集，並透過 `values.yaml` 自訂 KMS、OIDC 與 Worker 資源池配置。
2. 配置 `deploy/gitops/argocd-application.yaml` 連結 Git 倉庫。
3. ArgoCD 監聽 Git 變更，自動執行聲明式同步與漂移自我修復（Self-Healing），實現現代化企業級 GitOps 交付。

## Use Case：遇到 CAPTCHA 驗證碼的雙向即時遠端接管（HITL Takeover）

1. 某銀行供應商後台登入流程中突然觸發 Cloudflare Turnstile 驗證碼或手機簡訊 OTP。
2. 監控人員在 Operations Center 透過 WebSocket 即時串流察覺瀏覽器停留在驗證碼頁面，點擊 **`Pause (Takeover)`** 按鈕（呼叫 `POST /v1/tasks/{id}/pause`）。
3. Worker 進入暫停等待狀態，畫面標籤轉為橘色 `PAUSED (TAKEOVER)`。
4. 維運人員直接在網頁畫布上點選驗證碼核取方塊（觸發 `action: click`），並在輸入框填寫手機簡訊驗證碼點擊 `Send Keys`（觸發 `action: type`）。
5. 驗證通過並成功登入後，維運人員點選 **`Resume Task`** 按鈕（呼叫 `POST /v1/tasks/{id}/resume`）。
6. Worker 自動脫離暫停狀態繼續推進後續爬蟲與截圖任務，並將人機介入操作歷程完整留存於 Audit Log 與任務 Metadata 中，避免整個流程直接失敗中斷。

## Use Case：跨瀏覽器核心（Chromium / Firefox / WebKit）矩陣相容性驗證

1. 電商前端團隊推出新版結帳流程，需要驗證在三大瀏覽器核心下的排版渲染與 JavaScript 相容性。
2. 開發人員在 Operations Center 點選 **`Dispatch Matrix (3 Engines)`** 按鈕（呼叫 `POST /v1/tasks/matrix`）。
3. 系統自動平行生成 3 個 Task，分別指派給 Chromium、Firefox 與 WebKit 內核執行。
4. Worker 資源池獨立啟動三種瀏覽器執行相同的購物車與結帳指示。
5. 執行完成後，團隊在 **`Cross-Browser Matrix Comparison`** 面板一覽聚合報告：比對三大核心之總耗時、Verdict 評估結果、DOM 自癒情形與截圖產物，快速揪出 WebKit 特有的排版跑版問題。

## Use Case：Zero-Trust 動態高斯模糊遮罩與機密 Token 防洩

1. 某營運任務需要填寫使用者帳號密碼與 API 金鑰以執行外部系統查詢。
2. 啟用了 Zero-Trust DLP 防護後，系統在瀏覽器 DOM 渲染時自動為 `input[type="password"]` 注入動態 CSS 高斯模糊遮罩（`filter: blur(8px)`）。
3. 任何透過 WebSocket 即時推播之畫面幀、截圖 Artifact 或 WebM 視訊錄影，在影像源頭即已模糊不可辨識，即使錄影檔被外部非授權人員存取，亦無法窺探真實密碼。
4. 同時，任務執行過程中產生的日誌與 Metadata 中的 Authorization Bearer Token 和 sk-... API Keys 自動被替換為 `[REDACTED_TOKEN]`，杜絕敏感資料外洩至 APM 或資料庫。

## Use Case：多叢集排程同盟跨區域 Leader 自動切換與容災接管

1. 企業在東京區域（`ap-northeast-1`）與大阪區域（`ap-northeast-3`）部署了兩個獨立的 BrowserAgent 叢集，共同維護全球業務排程。
2. 東京節點作為同盟中的 Primary Leader，每 5 秒向同盟發送心跳以維持排程租約（Lease TTL 15 秒），並負責派發 Cron 巡檢。
3. 當東京機房發生電力中斷或主機離線，其心跳逾期停止刷新。
4. 大阪備援節點在偵測到 Leader 租約過期後，自動依優先權晉升為新 Leader，無縫接管所有定時巡檢派發工作，全程無需人工介入，保證業務零中斷。
5. 系統管理者亦可隨時在 Operations Center 點擊 **`Force Re-election`** 進行災備演練或例行維護的主從切換。

# BrowserAgent V1.3 詳細版本規劃書（完整對齊版）
## 主軸：Enterprise OIDC SSO, KMS Envelope Encryption, WebSocket Live Broadcast, Self-Healing & Helm GitOps

---

## 1. 深度對照與調整動機（ROADMAP & 限制分析）

在重新深入比對 [`DOCS/ROADMAP.md`](file:///e:/GenAI/1.ProductionProject/0.Bak/BrowserAgent/DOCS/ROADMAP.md)、[`DOCS/IMPLEMENTATION_STATUS.md`](file:///e:/GenAI/1.ProductionProject/0.Bak/BrowserAgent/DOCS/IMPLEMENTATION_STATUS.md) 與 [`DOCS/OVERVIEW.md`](file:///e:/GenAI/1.ProductionProject/0.Bak/BrowserAgent/DOCS/OVERVIEW.md) 的「目前限制」與「未來規劃候選」後，我們發現現有系統存在四項核心限制，且文件已明確定義了 V1.3 的演進目標。

本次規劃書進行**全面調整與深度對齊**，將文件中列出的未來功能 100% 納入規劃架構，並針對專案規範（如 Heuristic 不接外部 LLM）制定最務實的落地設計。

---

### 1.1 文件規劃項目 vs. V1.3 落地對照矩陣

| 文件來源 | 記錄之未來規劃 / 限制項目 | 原規劃盲點 / 現狀限制 | V1.3 調整後之落地架構方案 |
|---|---|---|---|
| **OVERVIEW 限制 1**<br>**STATUS 項目 1** | **完整 IdP Authorization Code Flow**（第三方 IdP 登入導頁與前端 Session 管理） | 原規劃遺漏此項目。<br>現狀僅支援 Header Bearer token 與 Local dev token，前端 UI 無法透過第三方 IdP（Keycloak/Auth0/Okta）完成 OAuth2 授權導頁。 | **新增完整 OIDC Auth Code 登入流程**：實作 `/v1/auth/oidc/login` 導頁、`/v1/auth/oidc/callback` 授權碼交換、HttpOnly Secure Cookie 管理與 Operations Center SSO 登入按鈕。 |
| **OVERVIEW 限制 2**<br>**STATUS 項目 3** | **Helm Chart 封裝發佈與 GitOps (ArgoCD/Flux) 範本** | 現狀僅有 `deploy/k8s/` 靜態 Kustomize YAML，企業無法透過 `helm install` 客製化參數。 | **新增標準 Enterprise Helm 3 Chart 套件（`deploy/helm/browser-agent/`）** 與 `deploy/gitops/argocd-app.yaml` 範本。 |
| **OVERVIEW 限制 3**<br>**STATUS 項目 2** | **外部金鑰管理整合（HashiCorp Vault / AWS KMS 信封加密）** | 現狀 Session Vault 之 `storage_state` 為明文 JSON，缺乏落盤加密。 | **實作 KMS 信封加密架構（Envelope Encryption）**：支援 `LocalKmsProvider`（AES-256-GCM 主金鑰衍生）與 `AwsKmsProvider` / `VaultKmsProvider` 介面，使用 Data Encryption Key (DEK) 加密 Session Payload，落盤完全密文化。 |
| **OVERVIEW 限制 4**<br>**STATUS 項目 5** | **瀏覽器操作錄影的即時 WebSocket 串流（Live Screen Broadcast）** | 現狀 WebM 視訊需等待任務結束才產出，執行中狀態存在黑盒盲區。原規劃僅用 SSE 暫態幀。 | **新增 WebSocket 低延遲螢幕直播廣播（Live Screen Broadcast）**：Worker 於 Playwright 執行迴圈中透過 WebSocket 串流畫面幀至 Operations Center 即時 Canvas 播放器，並支援線上中斷（Abort）。 |
| **STATUS 項目 4**<br>**ROADMAP 項目 5** | **自我修復瀏覽器動作（Self-Healing Browser Actions）** | ROADMAP 提及 LLM 自癒，但 `AGENTS.md` 規範明確要求「Planner 目前是 heuristic，不接外部 LLM」。 | **實作「啟發式特徵自癒引擎（Heuristic DOM Self-Healing Engine）」**：採多層級選擇器降級與 DOM 啟發式特徵距離比對（Text, Aria, Role, Parent），兼顧自癒穩定性且 100% 遵守 Heuristic 規範。 |
| **ROADMAP 項目 2** | **多區域多叢集排程調度與租戶專屬 Worker 資源池隔離** | 現狀所有任務共享單一 Kafka topic，低優先級任務阻塞高優先級巡檢。 | **實作三級加權優先佇列（High / Default / Batch）與租戶專屬 Worker Pool 路由**。 |

---

## 2. V1.3 六大核心功能模組詳細規格

### 模組一：完整 OIDC Authorization Code Flow & 前端工作階段治理
- **為什麼要做**：解決目前 Operations Center 只能手動貼上 Token 的維運痛點，讓企業員工、稽核員可直接點選「SSO Login with IdP」，符合企業單一登入標準。
- **架構設計**：
  1. `GET /v1/auth/oidc/login`：產生 `state` 與 `code_verifier`（PKCE），儲存於 Redis，並重導向至 IdP（如 Keycloak、Okta、Google Workspace）。
  2. `GET /v1/auth/oidc/callback`：接收授權碼 `code`，向 IdP Token Endpoint 交換 ID Token 與 Access Token，驗證簽名後提取使用者資訊與 Role。
  3. 發行帶有 HttpOnly、SameSite=Lax 的 Session Cookie（`ba_session`）。
  4. `POST /v1/auth/logout`：清除 Session 並支援 OIDC RP-Initiated Logout。
  5. Operations Center 頂部加入「SSO Login / Logout」切換狀態與當前登入者資訊展示。

### 模組二：企業級金鑰管理與 Session 信封加密（KMS Envelope Encryption）
- **為什麼要做**：徹底落實 SOC2 與 PCI-DSS 合規性要求，保證已登入之敏感 Session Cookies 與 LocalStorage 在落盤（S3 或 Local FS）時絕對不以明文形式存在。
- **架構設計**：
  1. **信封加密架構**：
     - **Key Encryption Key (KEK)**：由本機安全金鑰、AWS KMS（`kms:GenerateDataKey`）或 HashiCorp Vault 管理。
     - **Data Encryption Key (DEK)**：由 KEK 派生或動態生成之對稱金鑰（AES-256）。
  2. **加密流程**：
     - Playwright 產出 `storage_state` JSON。
     - 產生動態 DEK，使用 AES-256-GCM 加密 Session 資料。
     - 使用 KEK 加密 DEK，產生 `encrypted_dek`。
     - 密文 Payload 寫入 ArtifactStore，Metadata 記錄 `{"kms_provider": "local|aws|vault", "key_id": "...", "encrypted_dek": "...", "algorithm": "AES-256-GCM"}`。
  3. **解密流程**：
     - TaskRunner 載入 Session 時，呼叫 KMS 解密 DEK，再於記憶體中解密 Session Payload，直接注入 Playwright Context，全程不落明文磁碟。
  4. **金鑰輪換（Key Rotation）**：支援舊金鑰解密與新金鑰重加密端點。

### 模組三：瀏覽器即時畫面 WebSocket 廣播串流（Live Screen Broadcast）
- **為什麼要做**：打破 V1.2 必須等待整個任務執行完畢才能看 WebM 影片的限制，提供即時執行的低延遲監控與即時異常干預能力。
- **架構設計**：
  1. **Worker 端畫面捕獲**：
     - Playwright 執行每一步動作前後或在等待期間，以輕量方式截取最新畫面幀（JPEG，品質 70%，記憶體壓縮）。
     - 將畫面幀發布至 Redis Pub/Sub 頻道（`live_stream:{task_id}`）。
  2. **API 端 WebSocket 橋接**：
     - 提供 `WS /v1/tasks/{task_id}/live-stream` 端點。
     - 維運人員連線後，訂閱 Redis 頻道並將畫面幀以二進位（Binary Blob）即時推送至客戶端。
  3. **前端 Operations Center 即時播放器**：
     - 內建 HTML5 Canvas 接收 WebSocket 二進位數據並高速繪製，呈現流暢的「Live Screen Broadcast」。
     - 畫面上方提供「● LIVE」紅色指示燈、當前執行步驟提示與「Abort Execution」按鈕。
  4. **即時中斷機制（Abort）**：
     - 操作員點擊「Abort」時，呼叫 `POST /v1/tasks/{task_id}/abort`，Redis 設置中斷標記，Worker 在下一個操作循環即刻拋出 `ExecutionAbortedException`，安全關閉瀏覽器並將任務標記為 `aborted`。

### 模組四：啟發式選擇器自我修復引擎（Heuristic Self-Healing）
- **為什麼要做**：提升前端改版時自動化腳本的自癒存活率，且**100% 遵守 `AGENTS.md`「Planner 目前是 heuristic，不接外部 LLM」之核心規範**。
- **架構設計**：
  1. **選擇器降級階層鏈（Selector Fallback Cascade）**：
     - 允許在 Step 中指定 `fallback_selectors: [CSS, XPath, Text, Aria]`。
  2. **啟發式特徵相似度比對（Heuristic DOM Matcher）**：
     - 當首選選擇器逾時失效時，觸發 Heuristic 自癒評估。
     - 分析當前頁面 DOM 結構，比對候選元素的：
       - `text_content`（Levenshtein 編輯距離）
       - `aria-label` / `role`
       - `name` / `placeholder` / `data-testid`
       - 父節點結構相對路徑
     - 計算綜合置信度評分（0.0 ~ 1.0），超過閥值（0.75）即自動嘗試該候選元素。
  3. **自癒軌跡與指標**：
     - 自癒成功時，Step 記錄 `self_healed: true`、`original_target`、`healed_target`、`strategy`。
     - 寫入 `task.self_healed` 審計日誌，TraceBuffer 記錄自癒事件。
     - Operations Center 視覺化回放以綠色閃電徽章標註該步驟。

### 模組五：Enterprise Helm 3 Chart 套件與 GitOps (ArgoCD) 藍圖
- **為什麼要做**：將 V1.2 的靜態 K8s Kustomize 清單封裝為企業雲原生主流標準，支援一鍵部署、靈活參數配置與宣告式持續交付。
- **架構設計**：
  1. 目錄結構：`deploy/helm/browser-agent/`
     - `Chart.yaml`：版本 V1.3.0，應用程式描述。
     - `values.yaml`：宣告式配置（副本數、映像檔、資源配額、Ingress TLS、KMS 金鑰、Redis/Kafka 連線、KEDA 擴縮設定）。
     - `templates/`：包含 API Deployment、Worker Deployment、Service、Ingress、ConfigMap、Secret、KEDA ScaledObject、ServiceMonitor。
  2. GitOps 範本：`deploy/gitops/argocd-application.yaml`
     - 支援 ArgoCD 自動同步與健康檢查配置。
  3. 自動化驗證：納入 `helm lint` 與 `helm template` 測試。

### 模組六：多優先權加權佇列與租戶專屬 Worker 資源池
- **為什麼要做**：徹底解決 Noisy Neighbor 效應，保障重要定時巡檢與高風險任務的 SLA。
- **架構設計**：
  1. Kafka 佇列分為：`agent.tasks.high`（priority $\ge$ 8）、`agent.tasks.default`（priority 3~7）、`agent.tasks.batch`（priority $\le$ 2）。
  2. Worker 支援加權輪詢消費（5 : 3 : 1）或專屬佇列 Worker 標籤（`WORKER_POOL=high-only`）。
  3. Operations Center 提供各優先級佇列的即時 Lag 狀態。

---

## 3. UI / Operations Center V1.3 互動後台設計

自 V1.0 起，主要營運入口為 `/operations`。V1.3 將針對新功能進行深度介面整合：

```
+---------------------------------------------------------------------------------------------------------+
| Browser Agent v1.3 Operations Center  [System: Normal]  [OIDC: Enabled]  [Vault: KMS-Encrypted]        |
| [Refresh] [Register Skills] [SSO Login/Logout] [Approve Selected]                                       |
+----------------------------------------------------+----------------------------------------------------+
| 左側：維運控制與基礎治理                           | 右側：任務詳情、即時串流與進階回放                |
| 1. Operations & Production Readiness (含 KMS 檢查) | 1. Task Detail & Policy (含優先權分流標籤)        |
| 2. Queue & Worker Pools 狀態 (High/Default/Batch)  | 2. Planner & SkillHub (含 Self-Healing 統計)       |
| 3. Production Alerting Center (7 大規則 + Webhook) | 3. Status Flow & Audit Timeline                    |
| 4. Scheduled Tasks 巡檢調度 (Cron / Run Now)       | 4. Live Screen Broadcast (WebSocket 直播 + Abort)  |
| 5. Session Vault 保險箱 (KMS 加密狀態與驗證)       | 5. Visual Step Replay (含 Self-Healing 綠色標籤)   |
| 6. Reliability / DLQ (Bulk Replay / Quarantine)    | 6. Full WebM Video Player (全行程視訊回放)         |
| 7. Recent Tasks 清單                               | 7. Trace Inspector (跨進程 Span 追蹤樹)            |
+----------------------------------------------------+----------------------------------------------------+
```

### 關鍵 UI 互動驗證點：
1. **OIDC SSO 登入驗證**：點擊「SSO Login」，跳轉或模擬 IdP 授權導頁，回調後徽章轉為「OIDC: Authenticated (operator@corp)」。
2. **KMS Session 憑證安全驗證**：Session 清單中每一筆均標示「Encrypted: AES-256-GCM (KMS)」，點擊「Validate」按鈕可測試解密連通性。
3. **Live Screen Broadcast 觀看與中斷**：點選執行中（executing）任務時，Live Canvas 即時以 WebSocket 顯示當前瀏覽器畫面；點擊「Abort Execution」按鈕即刻中斷任務。
4. **Self-Healing 綠色自癒標章**：在步驟回放中，點擊自癒步驟可查看修復前後的 Selector 與特徵相似度得分。

---

## 4. API 變更規格（全面相容）

| 端點 | 方法 | RBAC 權限 | 說明 |
|---|---|---|---|
| `/v1/auth/oidc/login` | GET | public | 發起 OIDC 授權碼重導向 |
| `/v1/auth/oidc/callback` | GET | public | 處理 IdP 回調，核發 Session Cookie |
| `/v1/auth/logout` | POST | all | 登出並清除 Session |
| `/v1/tasks/{task_id}/live-stream` | WS | viewer/creator/operator/admin | 建立 WebSocket 雙向串流通道，傳輸二進位畫面幀 |
| `/v1/tasks/{task_id}/abort` | POST | operator/admin | 中斷執行中任務 |
| `/v1/sessions/{session_name}/validate` | POST | operator/admin | KMS 解密並驗證 Session 憑證有效性 |
| `/v1/ops/queues` | GET | operator/admin | 查詢 High/Default/Batch 各佇列的 Lag 與 Worker 分布 |
| `/v1/ops/kms/status` | GET | operator/admin | 檢查 KMS / Vault 金鑰連通性與 Provider 狀態 |

---

## 5. 測試項目與驗證命令

### 5.1 預計新增測試模組
- `tests/test_oidc_auth.py`：驗證 Auth Code 流程、PKCE 交換、Session Cookie 與 RBAC 綁定。
- `tests/test_kms_envelope.py`：驗證 KMS Provider、DEK 加解密、資料篡改防護與 Session Vault 整合。
- `tests/test_live_stream_ws.py`：驗證 WebSocket 畫面幀廣播、多客戶端訂閱與 Abort 中斷機制。
- `tests/test_self_healing.py`：驗證 Heuristic DOM 選擇器修復、特徵距離比對與 Metadata 記錄。
- `tests/test_multi_priority.py`：驗證 High/Default/Batch 加權消費分流。
- `tests/test_helm_package.py`：驗證 Helm Chart 語法、模板渲染與默認 values。

### 5.2 驗證執行命令
```powershell
# 1. 完整自動化測試
pytest -q

# 2. 靜態編譯與語法檢查
python -m compileall src tests worker alembic
git diff --check

# 3. Helm Chart 檢驗
helm lint deploy/helm/browser-agent/
helm template test-release deploy/helm/browser-agent/

# 4. Docker Compose 整合測試
docker compose up -d --build
docker compose exec -T api pytest -q
```

---

## 6. 文件 100% 同步規劃清單

測試通過後，嚴格落實專案工作規範，全面同步更新以下 15 份核心文件：
1. `README.md`（一般版只同步版本號至 V1.3，技術版全面完整更新）
2. `DOCS/OVERVIEW.md`（更新版本重點，消除已解決之 4 大限制）
3. `DOCS/API.md`（更新 OIDC、WebSocket、Abort、KMS、Queue APIs 規格）
4. `DOCS/ARCHITECTURE.md`（更新架構圖資產與流程圖，納入 KMS、WebSocket、OIDC、Helm）
5. `DOCS/CONFIGURATION.md`（新增 OIDC、KMS_PROVIDER、KMS_KEY_ID、MULTI_PRIORITY 變數說明）
6. `DOCS/DATA_MODEL.md`（更新 Task Metadata、Session Encryption Metadata 結構）
7. `DOCS/IMPLEMENTATION_STATUS.md`（同步已完成清單與版本摘要）
8. `DOCS/ROADMAP.md`（將 V1.3 標記完成，規劃 V1.4 候選）
9. `DOCS/RUNBOOK.md`（新增 OIDC IdP 配置、KMS 金鑰管理、Helm 部署與 Abort 維運步驟）
10. `DOCS/SECURITY_AND_POLICY.md`（新增 OIDC SSO 安全規範、KMS 信封加密政策）
11. `DOCS/OBSERVABILITY.md`（新增 WebSocket 連線指標、多優先權佇列 Lag 指標）
12. `DOCS/TEST_REPORT.md`（記錄 V1.3 真實測試數據，預計達 100+ tests 通過）
13. `DOCS/USE_CASES.md`（新增 SSO 登入情境、KMS 憑證治理、Live 直播排查與自癒情境）
14. `DOCS/DEVELOPMENT.md`（新增 V1.3 開發環境、Helm 本機除錯與測試說明）
15. `DOCS/manual_test.md`（**規範必備**：新增 Operations Center V1.3 完整人工測試步驟、FAQ 與 Checklist）

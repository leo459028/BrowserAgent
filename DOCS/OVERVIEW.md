# Overview

`BrowserAgent` 目前是 **V1.4：Bidirectional Remote Takeover (HITL), Cross-Browser Matrix Execution (Chromium/Firefox/WebKit), Zero-Trust Dynamic DLP, Multi-Cluster Federation & Operations Center V1.4**。此版本把 control plane、worker、artifact governance、Auth/RBAC、reliability foundation、production readiness、端到端分散式追蹤、生產告警中心、視覺化步驟回放、定時巡檢調度引擎、工作階段保險箱、全行程瀏覽器 WebM 錄影播放、OpenTelemetry OTLP 批次導出、Kubernetes / Helm 生產級佈署套件、**雙向即時遠端接管、跨瀏覽器矩陣執行、Zero-Trust DLP 防洩保護與多叢集同盟容災**整理成完整的企業級營運後台與自動化平台。

## 版本重點

- v0.1-v0.6 建立 browser task lifecycle、approval、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock 與 DLQ replay 基礎。
- v1.0 新增 `Browser Agent Operations Center`、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1 新增 Compose Production Readiness、OIDC discovery、端到端分散式追蹤（W3C Traceparent & Spans 呼叫鏈）、Production Alerting Center（7 大即時維運規則與非阻塞 Webhook 轉發）、以及 Visual Step Replay（步驟分頁條 + 即時截圖縮圖/DOM 預覽）。
- v1.2 新增 Scheduled Tasks 定時巡檢調度引擎（Cron 表達式解析、Redis 分散式搶鎖、防重入派發）、Session Vault 工作階段保險箱（Playwright `storage_state` 憑證治理、自動跨任務注入、一鍵撤銷）、全行程 WebM 瀏覽器視訊錄製與播放器（WebM Artifact 保存與 Operations Center 播放）、OpenTelemetry OTLP 批次導出（非同步背景 Batch Span 推送至 APM）、以及生產級 Kubernetes Manifests 套件（`deploy/k8s/`）與 KEDA Kafka 消費者自動水平擴展藍圖。
- v1.3 新增 Enterprise OIDC Authorization Code Flow（PKCE、防偽 state、HttpOnly `ba_session` Cookie、前端 SSO 登入）、Session Vault 企業級 KMS 信封加密（Local / AWS KMS / Vault 驅動、AES-256-GCM、AAD 租戶隔離、金鑰輪換驗證）、啟發式多維選擇器自我修復引擎（Heuristic Self-Healing，Fallback cascade、DOM 特徵比對、自癒日誌與綠色標籤）、多優先權加權佇列與 Worker 資源池隔離（High/Queued/Batch 路由、`/v1/ops/queues` 監控）、瀏覽器即時畫面 WebSocket 廣播串流與線上中斷（`WS /v1/tasks/{id}/live-stream`、`POST /v1/tasks/{id}/abort`）、以及 Enterprise Helm 3 Chart 套件（`deploy/helm/browser-agent/`）與 GitOps ArgoCD 藍圖。
- v1.4 新增 雙向即時遠端接管與人機協作（HITL Reverse Control Channel，線上暫停、滑鼠/鍵盤遠端注入、介入歷程審計）、跨瀏覽器矩陣執行引擎（Chromium / Firefox / WebKit 核心原生支援、一鍵派發矩陣任務、跨引擎渲染與耗時聚合比對）、Zero-Trust 動態資料防洩保護（CSS 高斯模糊像素遮罩、Bearer Token / API Key 正則脫敏、Metadata 遞迴過濾）、多叢集排程同盟與容災接管（分散式心跳租約、Leader Election、腦裂防護、`/v1/ops/federation/re-election` 強制主從切換）、以及 Operations Center V1.4 升級（DLP 與同盟狀態徽章、雙向接管操控條、矩陣比較面板）。

## 文件索引

| 文件 | 內容 |
|---|---|
| [README.md](../README.md) | 主要入口與快速啟動 |
| [API.md](./API.md) | Auth（Local/JWKS/OIDC）、task、scheduled task、session（KMS/Validate）、video、live-stream、abort、queues、approval、artifact、DLQ、replay、operations、alerts、traces、**takeover、interact、pause/resume、matrix、DLP、federation APIs** |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Control plane、data plane、governance layer、**雙向控制通道、多內核執行緒池、DLP 防洩管線、多叢集同盟架構**；架構圖資產：繁中版 `browseragent-architecture-v1.4ch.png`、英文版 `browseragent-architecture-v1.4en.png` |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、production-like config、Kubernetes manifests、Helm values、OIDC/KMS/Priority/LiveStream/**DLP/Federation/BrowserEngine settings** |
| [DATA_MODEL.md](./DATA_MODEL.md) | SQLAlchemy model、`cluster_nodes` 表、`tasks`（browser_engine, matrix_id, human_intervened, dlp_masked）擴充欄位、session KMS 加密 metadata、audit metadata |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Auth/RBAC、PKCE OIDC、KMS 信封加密、**Zero-Trust DLP 像素遮罩、反向操控通道存取控制、同盟租約認證**、artifact access、DLQ controls |
| [RUNBOOK.md](./RUNBOOK.md) | 本機、Docker、Kubernetes 與 Helm 驗證流程、**HITL 人工介入維運、跨瀏覽器資源排查、同盟主從切換與故障排查** |
| [USE_CASES.md](./USE_CASES.md) | Operations Center 情境、Scheduled Tasks 巡檢、Session KMS 治理、Live Stream、**CAPTCHA 人工接管、跨瀏覽器矩陣佈局驗證、DLP 機密防洩、跨區域同盟容災** |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health、metrics、logging、audit、readiness、alerting、tracing、OTLP streaming、Queues & Live 監控、**DLP 脫敏計數、HITL 介入耗時與同盟節點拓撲** |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成與尚未完成項目 |
| [ROADMAP.md](./ROADMAP.md) | 版本規劃 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 開發環境、20 個測試模組與 Bootstrap 指引 |
| [manual_test.md](./manual_test.md) | Operations Center 完整人工測試步驟與 FAQ |
| [TEST_REPORT.md](./TEST_REPORT.md) | 實際測試結果（105 項測試、真實瀏覽器與 Docker 驗證數據） |

## 目前限制

- 提供完整 Kubernetes Kustomize 套件、Enterprise Helm 3 Chart 與 GitOps ArgoCD 藍圖，正式上線仍需依各企業雲端網路（AWS EKS/GCP GKE/Azure AKS）配置對應之 Cloud Ingress Controller 與真實雲端 KMS 金鑰。
- 選擇器自我修復引擎採用啟發式特徵比對與多層 Fallback Cascade 演算法，未引入外部非同步視覺大型語言模型，保證系統低延遲、確定性與零機密外洩。
- 雙向即時接管通道目前支援 click、type、press 等基礎動作注入，尚未支援多游標拖曳與複雜手勢。
- 多叢集同盟依賴 Redis 分散式租約與心跳，跨區域延遲較高時需適當調整租約逾時時間（預設 15 秒）。
- 跨瀏覽器矩陣執行需確保 Worker 節點具有安裝對應之瀏覽器二進位檔（Playwright chromium, firefox, webkit）。

# Roadmap

Roadmap 以可查詢、可驗證的 implementation slice 為單位。V1.0 起，主要 UI 入口是 `/operations`。

## 已完成

- v0.1-v0.6：browser task flow、approval、audit、metrics、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock、DLQ replay。
- v1.0：Operations Center、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1：端到端分散式追蹤（W3C traceparent、Span 生命週期、記憶體 TraceBuffer、跨服務 Trace Inspector）、生產告警中心（Production Alerting Center、7 大維運規則即時評估、外部 Webhook/Slack/Discord 非阻塞轉發與手動測試派發）、可視化步驟回放（Visual Step Replay：步驟分頁條、點選即時預覽截圖縮圖、DOM 摘要）、Compose Production Readiness、OIDC discovery。
- v1.2：Scheduled Tasks 定時巡檢調度引擎（Cron 表達式解析、Redis 分散式搶鎖、防重入調度、手動派發）、Session Vault 工作階段保險箱（Playwright storage_state 憑證安全隔離、自動注入免重複登入、一鍵撤銷）、全行程 WebM 視訊錄製與撥放（WebM 影片 Artifact 保存、Operations Center 內建 HTML5 播放器與串流）、OpenTelemetry OTLP Exporter（非同步背景 Batch Span 推送至 Jaeger/Tempo/Datadog）、Kubernetes 生產 Manifests 套件（`deploy/k8s/` Kustomization）與 KEDA Kafka 消費者自動水平擴展藍圖。
- v1.3：Enterprise OIDC Authorization Code Flow（PKCE、state 防偽、`ba_session` Cookie、SSO 登入）、Session Vault 企業級 KMS 信封加密（Local/AWS/Vault 驅動、AES-256-GCM、AAD 租戶隔離、金鑰輪換）、啟發式選擇器自我修復引擎（Heuristic Self-Healing，三級 Fallback Cascade、DOM 標籤特徵比對、自癒日誌與標籤）、多優先權加權佇列分流與 Worker 資源池隔離（High/Queued/Batch 路由、`/v1/ops/queues` 監控）、瀏覽器即時畫面 WebSocket 廣播串流與線上中斷（`WS /v1/tasks/{id}/live-stream`、`POST /v1/tasks/{id}/abort`）、Enterprise Helm 3 Chart 套件（`deploy/helm/browser-agent/`）與 GitOps ArgoCD 藍圖，以及 Operations Center V1.3 集中營運介面。

## V1.4 / 未來規劃候選

- 多區域多叢集 Active-Active 排程調度與異地容災同步（Multi-Region Federation）。
- 雙向即時遠端接管與調試控制台（Interactive Remote Takeover / Human-in-the-Loop WebRTC Console）。
- 基於多模態視覺大模型的深度語意理解與自適應行動規劃（VLM Semantic DOM Comprehension）。
- 自動生成式跨瀏覽器相容性測試矩陣（Cross-Browser Grid Matrix Execution）。
- 零信任端點設備指紋與動態情境訪問控制（Zero-Trust Device Fingerprinting）。

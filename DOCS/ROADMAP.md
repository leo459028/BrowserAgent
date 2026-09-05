# Roadmap

Roadmap 以可查詢、可驗證的 implementation slice 為單位。V1.0 起，主要 UI 入口是 `/operations`。

## 已完成

- v0.1-v0.6：browser task flow、approval、audit、metrics、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock、DLQ replay。
- v1.0：Operations Center、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1：端到端分散式追蹤（W3C traceparent、Span 生命週期、記憶體 TraceBuffer、跨服務 Trace Inspector）、生產告警中心（Production Alerting Center、7 大維運規則即時評估、外部 Webhook/Slack/Discord 非阻塞轉發與手動測試派發）、可視化步驟回放（Visual Step Replay：步驟分頁條、點選即時預覽截圖縮圖、DOM 摘要）、Compose Production Readiness、OIDC discovery。
- v1.2：Scheduled Tasks 定時巡檢調度引擎（Cron 表達式解析、Redis 分散式搶鎖、防重入調度、手動派發）、Session Vault 工作階段保險箱（Playwright storage_state 憑證安全隔離、自動注入免重複登入、一鍵撤銷）、全行程 WebM 視訊錄製與撥放（WebM 影片 Artifact 保存、Operations Center 內建 HTML5 播放器與串流）、OpenTelemetry OTLP Exporter（非同步背景 Batch Span 推送至 Jaeger/Tempo/Datadog）、Kubernetes 生產 Manifests 套件（`deploy/k8s/` Kustomization）與 KEDA Kafka 消費者自動水平擴展藍圖。

## V1.3 / 未來規劃候選

- Helm Chart 封裝發佈與 GitOps (ArgoCD/Flux) 範本。
- 多區域多叢集 Active-Active 排程調度與租戶專屬 Worker 資源池隔離。
- Production 外部金鑰管理整合（HashiCorp Vault / AWS KMS 信封加密）。
- 完整 OIDC Authorization Code Flow（第三方 IdP 登入導頁與前端 Session 管理）。
- LLM 智慧自我修復（Self-Healing Browser Actions，在 DOM 變更或 Selector 失效時自動修復）。
- 瀏覽器操作錄影的即時 WebSocket 串流（Live Screen Broadcast）。

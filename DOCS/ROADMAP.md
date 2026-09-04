# Roadmap

Roadmap 以可查詢、可驗證的 implementation slice 為單位。V1.0 起，主要 UI 入口是 `/operations`。

## 已完成

- v0.1-v0.6：browser task flow、approval、audit、metrics、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock、DLQ replay。
- v1.0：Operations Center、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1：端到端分散式追蹤（W3C traceparent、Span 生命週期、記憶體 TraceBuffer、跨服務 Trace Inspector）、生產告警中心（Production Alerting Center、7 大維運規則即時評估、外部 Webhook/Slack/Discord 非阻塞轉發與手動測試派發）、可視化步驟回放（Visual Step Replay：步驟分頁條、點選即時預覽截圖縮圖、DOM 摘要）、Compose Production Readiness、OIDC discovery。

## V1.2 / 未來規劃候選

- Kubernetes manifests 或 Helm chart。
- Worker autoscaling 與動態消費者池擴縮。
- Production 外部金鑰管理（HashiCorp Vault / AWS KMS）。
- 正式 OpenTelemetry OTLP exporter（將記憶體 Spans 串流推送至 Jaeger / Tempo / Datadog）。
- 完整瀏覽器串流錄影（WebM 影片 Artifact 保存與撥放器）。
- 完整 OIDC Authorization Code Flow（登入導頁與 Session 管理）。

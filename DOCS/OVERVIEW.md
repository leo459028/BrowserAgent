# Overview

`BrowserAgent` 目前是 **V1.1：Production Readiness + End-to-End Tracing + Alerting Center + Visual Replay**。此版本把 control plane、worker、artifact governance、Auth/RBAC、reliability foundation、production readiness、端到端分散式追蹤、生產告警中心（含非阻塞 Webhook 轉發）與視覺化步驟回放，整理成可由 operator 查詢與操作的 `/operations` 入口。

## 版本重點

- v0.1-v0.6 建立 browser task lifecycle、approval、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock 與 DLQ replay 基礎。
- v1.0 新增 `Browser Agent Operations Center`、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1 新增 Compose Production Readiness、OIDC discovery、端到端分散式追蹤（W3C Traceparent & Spans 呼叫鏈）、Production Alerting Center（7 大即時維運規則與非阻塞 Webhook 轉發）、以及 Visual Step Replay（步驟分頁條 + 即時截圖縮圖/DOM 預覽）。

## 文件索引

| 文件 | 內容 |
|---|---|
| [README.md](../README.md) | 主要入口與快速啟動 |
| [API.md](./API.md) | Auth、task、approval、artifact、DLQ、replay、operations、alerts、traces APIs |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Control plane、data plane、governance layer；架構圖資產：繁中版 `browseragent-architecture-v1.1ch.png`、英文版 `browseragent-architecture-v1.1en.png` |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、production-like config、Auth/S3/OTEL-ready/Alerts settings |
| [DATA_MODEL.md](./DATA_MODEL.md) | SQLAlchemy model、metadata、audit、artifact fields |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Auth/RBAC、policy、artifact access、DLQ controls |
| [RUNBOOK.md](./RUNBOOK.md) | 本機與 Docker smoke test 流程與維運排查 |
| [USE_CASES.md](./USE_CASES.md) | Operations Center 情境 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health、metrics、logging、audit、readiness、alerting、tracing |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成與尚未完成項目 |
| [ROADMAP.md](./ROADMAP.md) | 版本規劃 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 開發環境、12 個測試模組與 Bootstrap 指引 |
| [manual_test.md](./manual_test.md) | Operations Center 完整人工測試步驟與 FAQ |
| [TEST_REPORT.md](./TEST_REPORT.md) | 實際測試結果（74 項測試與真實 Docker E2E 數據） |

## 目前限制

- V1.1 有 JWKS verifier 與 OIDC discovery，但未實作完整 IdP login/callback/session flow。
- Kubernetes/Helm、secrets vault、外部 OTLP Collector 遠端導出與完整影片串流錄影仍排在後續版本。
- Visual Step Replay 提供步驟截圖縮圖與 DOM 摘要回放，非即時 DOM 影片串流。

# Overview

`BrowserAgent` 目前是 **V1.2：Enterprise Session Vault, Task Scheduling, OTLP Streaming & Video Replay**。此版本把 control plane、worker、artifact governance、Auth/RBAC、reliability foundation、production readiness、端到端分散式追蹤、生產告警中心、視覺化步驟回放、定時巡檢調度引擎、工作階段保險箱、全行程瀏覽器 WebM 錄影播放、OpenTelemetry OTLP 批次導出，以及 Kubernetes 生產級佈署套件整理成完整的企業級營運後台與自動化平台。

## 版本重點

- v0.1-v0.6 建立 browser task lifecycle、approval、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock 與 DLQ replay 基礎。
- v1.0 新增 `Browser Agent Operations Center`、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。
- v1.1 新增 Compose Production Readiness、OIDC discovery、端到端分散式追蹤（W3C Traceparent & Spans 呼叫鏈）、Production Alerting Center（7 大即時維運規則與非阻塞 Webhook 轉發）、以及 Visual Step Replay（步驟分頁條 + 即時截圖縮圖/DOM 預覽）。
- v1.2 新增 Scheduled Tasks 定時巡檢調度引擎（Cron 表達式解析、Redis 分散式搶鎖、防重入派發）、Session Vault 工作階段保險箱（Playwright `storage_state` 憑證治理、自動跨任務注入、一鍵撤銷）、全行程 WebM 瀏覽器視訊錄製與播放器（WebM Artifact 保存與 Operations Center 播放）、OpenTelemetry OTLP 批次導出（非同步背景 Batch Span 推送至 APM）、以及生產級 Kubernetes Manifests 套件（`deploy/k8s/`）與 KEDA Kafka 消費者自動水平擴展藍圖。

## 文件索引

| 文件 | 內容 |
|---|---|
| [README.md](../README.md) | 主要入口與快速啟動 |
| [API.md](./API.md) | Auth、task、scheduled task、session、video、approval、artifact、DLQ、replay、operations、alerts、traces APIs |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Control plane、data plane、governance layer；架構圖資產：繁中版 `browseragent-architecture-v1.2ch.png`、英文版 `browseragent-architecture-v1.2en.png` |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、production-like config、Kubernetes manifests、Auth/S3/OTEL/Alerts/Scheduler settings |
| [DATA_MODEL.md](./DATA_MODEL.md) | SQLAlchemy model、scheduled_tasks 表、session/video artifact fields、audit metadata |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Auth/RBAC、policy、session security、artifact access、DLQ controls |
| [RUNBOOK.md](./RUNBOOK.md) | 本機、Docker 與 Kubernetes 驗證流程與維運排查 |
| [USE_CASES.md](./USE_CASES.md) | Operations Center 情境、Scheduled Tasks 巡檢、Session 治理情境 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health、metrics、logging、audit、readiness、alerting、tracing、OTLP streaming |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成與尚未完成項目 |
| [ROADMAP.md](./ROADMAP.md) | 版本規劃 |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 開發環境、17 個測試模組與 Bootstrap 指引 |
| [manual_test.md](./manual_test.md) | Operations Center 完整人工測試步驟與 FAQ |
| [TEST_REPORT.md](./TEST_REPORT.md) | 實際測試結果（84 項測試與真實驗證數據） |

## 目前限制

- V1.2 具備 JWKS verifier 與 OIDC discovery，但未實作完整第三方 IdP login/callback/session 導頁 flow。
- 提供完整 Kubernetes Kustomize 套件與 KEDA 藍圖，正式上線仍需依各企業雲端網路（AWS EKS/GCP GKE/Azure AKS）配置對應之 Cloud Ingress Controller 與 KMS 金鑰。
- Session Vault 以 ArtifactStore（Local/S3）進行隔離與生命週期管理，尚未整合 HashiCorp Vault / AWS KMS 信封加密。
- 視訊錄製為 Playwright WebM 格式全行程錄影，非即時 WebSocket 低延遲螢幕直播廣播。

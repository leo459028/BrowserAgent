# Overview

`BrowserAgent` 目前是 **V1.0 MVP：Operations Center**。此版本把 control plane、worker、artifact governance、Auth/RBAC 與 reliability foundation，整理成可由 operator 查詢與操作的 `/operations` 入口。

## 版本重點

- v0.1-v0.6 建立 browser task lifecycle、approval、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock 與 DLQ replay 基礎。
- v1.0 新增 `Browser Agent Operations Center`、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。

## 文件索引

| 文件 | 內容 |
|---|---|
| [README.md](../README.md) | 主要入口與快速啟動 |
| [API.md](./API.md) | Auth、task、approval、artifact、DLQ、replay、operations APIs |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Control plane、data plane、governance layer；架構圖資產：`DOCS/assets/browseragent-architecture.png` |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、Auth/S3 settings |
| [DATA_MODEL.md](./DATA_MODEL.md) | SQLAlchemy model、metadata、audit、artifact fields |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Auth/RBAC、policy、artifact access、DLQ controls |
| [RUNBOOK.md](./RUNBOOK.md) | 本機與 Docker smoke test 流程 |
| [USE_CASES.md](./USE_CASES.md) | Operations Center 情境 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health、metrics、logging、audit、readiness |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成與尚未完成項目 |
| [ROADMAP.md](./ROADMAP.md) | 版本規劃 |
| [TEST_REPORT.md](./TEST_REPORT.md) | 實際測試結果 |

## 目前限制

- V1.0 有 JWKS verifier，但未實作完整 IdP login / OIDC discovery flow。
- Kubernetes/Helm、secrets vault、OpenTelemetry tracing 與 browser 錄影仍排在後續版本。
- Replay-lite 使用 audit、steps、artifacts、evaluation 組成 timeline，不保存影片或 DOM stream。

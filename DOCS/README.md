# BrowserAgent 文件

最後更新：2026-05-20

`BrowserAgent` 是 enterprise browser agent platform 的 production-grade scaffold。目前完成 v0.2 lifecycle / approval / observability，以及 v0.3 artifact governance + Dashboard。

## 目前狀態

- v0.2：task lifecycle、policy decisions、approval flow、audit logs、metrics、worker execution、本機 Dashboard。
- v0.3：artifact backend abstraction、local artifact governance metadata、no-op redaction hook、tenant-scoped artifact access checks、`/demo` artifact query/testing UI。
- v0.4：尚未實作。Planner/SkillHub integration 是下一個主要方向。

## 文件列表

| 文件 | 用途 |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Runtime architecture、components、lifecycle、known gaps |
| [API.md](./API.md) | FastAPI endpoints、request/response shapes、Dashboard API |
| [DATA_MODEL.md](./DATA_MODEL.md) | ORM/schema model 與 metadata conventions |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、Kafka、artifacts |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | Local development 與 test commands |
| [RUNBOOK.md](./RUNBOOK.md) | Docker Compose verification 與 operational checks |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Policy、approval、artifact access boundaries |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health checks、metrics、audit、Dashboard observations |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已實作與待辦範圍 |
| [TEST_REPORT.md](./TEST_REPORT.md) | v0.2/v0.3 unit、integration、Docker、Dashboard test results |
| [ROADMAP.md](./ROADMAP.md) | v0.4 之後方向 |
| [USE_CASES.md](./USE_CASES.md) | Product use cases 與 operating scenarios |

## 重要說明

- API auth/RBAC 尚未實作；本機 API 使用固定 demo tenant/user UUIDs。
- Docker Compose 包含 MinIO，但 active artifact backend 仍是 `ARTIFACT_BASE_PATH` 底下的 local filesystem。
- Metrics 是 process-local；API `/metrics` 不會聚合 worker process counters。
- `/demo` 是本機 v0.3 Dashboard，用於測試與觀察，不是 production operator UI。

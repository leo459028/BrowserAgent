# BrowserAgent 文件總覽

最後更新：2026-05-21

`BrowserAgent` 是 enterprise browser agent platform 的 production-grade scaffold。此版本已完成 v0.4 Planner/SkillHub Dashboard implementation slice：task lifecycle、approval、observability、artifact governance、Planner schema validation、deterministic fallback，以及 SkillHub resolver metadata 都已可透過 API 與 `/demo` Dashboard 驗證。

## 目前完成範圍

- v0.1：Docker Compose demo stack、API、worker、Playwright browser task、screenshot/HTML artifacts。
- v0.2：task lifecycle、policy decision、approval flow、audit logs、metrics、Dashboard。
- v0.3：artifact backend abstraction、local artifact governance metadata、no-op redaction hook、tenant-scoped artifact access checks、Artifact Query UI。
- v0.4：Planner output validation、invalid output fallback、SkillHub resolver metadata、Planner/SkillHub Dashboard panel、Normal/Fallback/SkillHub E2E 測試。

## 文件列表

| 文件 | 內容 |
|---|---|
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Runtime architecture、components、lifecycle、Planner/SkillHub flow、known gaps |
| [API.md](./API.md) | FastAPI endpoints、request/response shape、Planner metadata、artifact access、Skill API |
| [DATA_MODEL.md](./DATA_MODEL.md) | ORM/schema model、task metadata convention、Planner/SkillHub metadata、artifact metadata |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose services、Kafka topics、artifact paths |
| [DEVELOPMENT.md](./DEVELOPMENT.md) | 本機開發、測試命令、Docker 測試、常見注意事項 |
| [RUNBOOK.md](./RUNBOOK.md) | Docker Compose 操作、Dashboard 測試、API E2E、troubleshooting |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Instruction scan、policy、approval、artifact access、Planner/SkillHub 安全邊界 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health checks、metrics、audit events、Dashboard 可觀測項目 |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成項目與尚未完成項目 |
| [TEST_REPORT.md](./TEST_REPORT.md) | Host、Docker、Dashboard、E2E 實際測試結果 |
| [ROADMAP.md](./ROADMAP.md) | v0.1 到 v1.0 的版本路線 |
| [USE_CASES.md](./USE_CASES.md) | 目前可展示與驗證的技術使用情境 |

## 重要限制

- API auth/RBAC 尚未實作；目前使用固定 demo tenant/user UUID。
- `/demo` 是本機測試 Dashboard，不是 production operator UI。
- Planner 仍是 heuristic，不接外部 LLM。
- SkillHub v0.4 只做 capability resolution metadata，不執行第三方 skill。
- Active artifact backend 仍是 local filesystem；MinIO 目前在 Compose 中提供，但程式尚未把 artifacts upload 到 MinIO。
- `/metrics` 是 process-local；API `/metrics` 不包含 worker process counters。

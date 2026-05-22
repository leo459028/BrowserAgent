# Overview

`BrowserAgent` 是 enterprise browser agent platform 的 production-grade scaffold。此版本已完成 v0.6 Reliability Foundation：在 v0.5 Auth/RBAC 與 Production Approval 之上，加入 task create idempotency、rate limiting、worker service identity、task lock、DLQ metadata 與 replay API。

## 版本重點

- v0.1：可執行的 Docker Compose demo stack。
- v0.2：task lifecycle、policy decision、approval flow、audit logs、metrics、Dashboard。
- v0.3：artifact backend abstraction、local artifact governance metadata、no-op redaction hook、tenant-scoped artifact access checks。
- v0.4：Planner output validation、invalid output fallback、SkillHub resolver metadata、Planner/SkillHub Dashboard panel。
- v0.5：local JWT auth、request-scoped tenant/user context、RBAC、production approval audit、v0.5 Dashboard identity panel。
- v0.6：idempotency、rate limiting、Redis/memory reliability store、worker service identity、task lock、DLQ replay、basic CI、v0.6 Dashboard Reliability / DLQ panel。

## 文件索引

| 文件 | 內容 |
|---|---|
| [README.md](../README.md) | 一般版與技術版入口 |
| [API.md](./API.md) | Auth、task、approval、artifact、skill API |
| [ARCHITECTURE.md](./ARCHITECTURE.md) | Control plane、data plane、governance layer、Auth/RBAC flow |
| [CONFIGURATION.md](./CONFIGURATION.md) | Environment variables、Docker Compose、Auth settings |
| [DATA_MODEL.md](./DATA_MODEL.md) | SQLAlchemy model、JWT actor、task metadata、approval/audit fields |
| [SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md) | Auth/RBAC、policy、approval、artifact access、Planner/SkillHub 邊界 |
| [RUNBOOK.md](./RUNBOOK.md) | 本機與 Docker smoke test 流程 |
| [USE_CASES.md](./USE_CASES.md) | Normal/Fallback/SkillHub/RBAC/Artifact 情境 |
| [OBSERVABILITY.md](./OBSERVABILITY.md) | Health、metrics、logging、audit |
| [IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md) | 已完成與尚未完成項目 |
| [ROADMAP.md](./ROADMAP.md) | 版本規劃 |
| [TEST_REPORT.md](./TEST_REPORT.md) | 實際測試結果 |

## 目前限制

- v0.6 使用本機 JWT，不接真實外部 OIDC/JWKS。
- `/demo` 是本機測試 Dashboard，不是正式 production operator UI。
- Planner 仍是 heuristic，不接外部 LLM provider。
- SkillHub 只做 capability resolution metadata，不執行第三方 skill。
- Artifact active backend 仍是 local filesystem。
- Metrics 為 process-local。
- Worker autoscaling、擴充部署與 production-grade browser isolation 仍待加強。

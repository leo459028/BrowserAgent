# Implementation Status

最後更新：2026-05-21

## 總覽

Repository 目前已完成 v0.4 implementation slice。這仍是 production-grade scaffold，不是完整 production product；尚未接入正式 auth/RBAC、外部 LLM、Kubernetes、DLQ 或 production artifact object storage。

## 已完成 Components

- FastAPI app factory 與 router。
- `/healthz`、`/readyz`、`/metrics`。
- `POST /v1/tasks`、`GET /v1/tasks`、`GET /v1/tasks/{task_id}`。
- `GET /v1/tasks/{task_id}/audit`。
- `POST /v1/tasks/{task_id}/approve`。
- `GET /v1/artifacts/{artifact_id}/content`。
- `POST /v1/skills`、`GET /v1/skills`。
- SQLAlchemy ORM models 與 Alembic initial migration skeleton。
- Kafka producer/consumer wrapper。
- Worker consumer loop 與 retry handling。
- Playwright browser runner。
- Heuristic Planner。
- v0.4 Planner schema validation 與 deterministic fallback。
- SkillHub registration 與 resolver metadata integration。
- Evaluator。
- Local artifact store 與 governance metadata。
- Artifact redaction hook interface，預設為 no-op。
- JSON logging。
- Docker Compose local stack。
- `/demo` v0.4 Dashboard。
- Bootstrap script：schema、demo tenant/user、Kafka topics。
- API 支援 `X-Correlation-ID`。

## v0.4 Planner Metadata

`TaskRunner` 會先呼叫 `HeuristicPlanner.plan()`，再用 `build_planner_metadata()` 驗證輸出。metadata 寫入 `tasks.metadata`：

```json
{
  "planner": {
    "version": "heuristic-v0.4",
    "valid": true,
    "source": "heuristic",
    "validation_errors": [],
    "fallback_used": false,
    "fallback_source": null,
    "skill_resolution": {
      "unresolved": ["browser.goto"],
      "unresolved_count": 1
    }
  },
  "plan": [
    {
      "action": "goto",
      "url": "https://example.com",
      "skill": {
        "name": "browser.goto",
        "version": null,
        "entrypoint": "builtin.browser.goto",
        "resolved": false
      }
    }
  ]
}
```

若 Planner output invalid，runner 會：
- 使用 deterministic fallback plan。
- 寫入 `planner.valid=false`。
- 寫入 `planner.validation_errors`。
- 寫入 `planner.fallback_used=true`。
- 產生 `task.plan_fallback_used` audit event。

## SkillHub Integration 現況

v0.4 將 browser action 視為 SkillHub capability：
- `browser.goto`
- `browser.click`
- `browser.fill`
- `browser.press`
- `browser.wait`
- `browser.extract_text`
- `browser.screenshot`

若 `SkillHub.resolve()` 找到 active skill，step `input_data.skill.resolved=true`。若找不到，step 繼續使用 builtin browser action，並標示 `resolved=false`。此版本不執行第三方 skill，也不新增工具執行器。

## Dashboard 現況

`GET /demo` 顯示 `Browser Agent v0.4 Dashboard`，可執行：
- normal planner task。
- fallback planner task。
- SkillHub resolved task。
- SkillHub missing task。
- redaction metadata task。
- high-risk、sensitive instruction、blocked-domain task。
- approval、runtime health、metrics、audit timeline、steps、evaluation、artifact preview、Artifact Query。

## 尚未完成

- OIDC/JWT auth 與 RBAC。
- Request-scoped tenant/user context。
- 外部 LLM provider integration。
- 真正執行第三方 SkillHub tool。
- Per-action confirmation。
- Redis locks、rate limiting、dedupe。
- DLQ 與 poison message replay tooling。
- Worker autoscaling。
- MinIO/S3 active artifact backend。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。
- Worker metrics endpoint 與 multiprocess metrics aggregation。

# Implementation Status

更新日期：2026-05-20

## 目前完成狀態

這個 repo 目前完成到 v0.2 completion/stabilization。它仍是 production-grade
scaffold，不是完整 production 產品，但 v0.2 需要的 lifecycle、approval policy、
observability 與本機 Dashboard 已補齊。

## 已實作

- FastAPI app factory 與 router。
- `/healthz`, `/readyz`, `/metrics`。
- `POST /v1/tasks` 建立 task。
- `GET /v1/tasks` 列出最近 task summary。
- `GET /v1/tasks/{task_id}` 讀取 task、steps、artifacts。
- `GET /v1/tasks/{task_id}/audit` 讀取單一 task audit timeline。
- `POST /v1/tasks/{task_id}/approve` 核准 task。
- `POST /v1/skills`, `GET /v1/skills`。
- SQLAlchemy ORM models。
- SQL schema 與 Alembic initial migration skeleton。
- Kafka producer/consumer wrapper。
- Worker consumer loop。
- Playwright browser runner 基本 action。
- Heuristic planner。
- Evaluator 基本評分。
- Local artifact store。
- JSON logging。
- Docker Compose local stack。
- `/demo` v0.2 Dashboard。
- `task_artifacts` artifact 摘要回傳與安全內容讀取 endpoint。
- Bootstrap script 建立 schema、seed demo tenant/user，並可建立 Kafka topics。
- API 支援 `X-Correlation-ID`，並寫入 task、event 與 audit payload。

## v0.2 行為

- allowlisted low/medium task 會進入 `pending_approval`。
- `risk_level=high|critical` 會進入 `pending_approval`，不再永久 `blocked`。
- sensitive instruction 會進入 `pending_approval`，例如 `login`, `password`, `payment`, `transfer`。
- 非 allowlist domain 會進入 `blocked`。
- prompt injection 類 instruction 會在 create task 階段回 400。
- approval 後 task 會進入 `queued`。
- Worker 只執行 `queued` task。
- Worker 執行時 task 會進入 `executing`。
- 成功後 task 會進入 `completed` 或 `review`。
- 失敗後 task 會進入 `failed`，並保存 error metadata。
- policy reason 會寫入 task metadata 與 audit payload。
- 核心 task metrics 已接入 create/executed/failed/duration；目前 `/metrics` 是 process-local，Docker Compose 下 API 不會自動匯總 Worker metrics。
- lifecycle audit 已覆蓋 created、pending approval、blocked、approved、queued、execution started、artifact written、evaluated、completed/review required、failed。

## v0.2 Dashboard

`GET /demo` 目前是本機 v0.2 Dashboard，可用來：

- 建立 allowlisted low-risk task。
- 建立 high-risk task 並觀察 `pending_approval`。
- 建立 sensitive instruction task 並觀察 `pending_approval`。
- 建立 blocked-domain task 並觀察 `blocked`。
- 核准 `pending_approval` task。
- 查看最近 tasks。
- 查看 status flow。
- 查看 metrics。
- 查看 audit timeline。
- 查看 steps、evaluation、screenshot 與 HTML artifact。

## 尚未實作

- 正式登入、OIDC/JWT auth。
- RBAC 與正式 approver role。
- 正式多租戶 request context。
- Planner output schema validation。
- SkillHub resolver 與 planner/runner 整合。
- Per-action policy/confirmation。
- Redis locks/rate limiting/dedupe 的核心流程接入。
- DLQ 與 poison message handling。
- Worker autoscaling。
- MinIO/S3 artifact upload。
- Artifact retention/redaction。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。
- 跨 process metrics 匯總，或獨立 scrape Worker metrics endpoint。

## 建議下一步

1. 以 v0.3 開始 artifact 與治理補強。
2. 抽象 artifact backend，加入 MinIO/S3。
3. 補 artifact metadata、retention、redaction 與 access control。
4. 等 v0.3 穩定後，再進 v0.4 Planner/SkillHub 整合。

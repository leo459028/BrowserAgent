# Implementation Status

最後更新：2026-05-20

## 目前狀態

Repository 目前已實作到 v0.3。它仍是 production-grade scaffold，不是完整 production product。

已實作：

- v0.2 task lifecycle、approval policy、observability、audit coverage、metrics、worker execution、本機 Dashboard。
- v0.3 artifact governance：storage abstraction、local backend metadata、no-op redaction hook、tenant-scoped artifact access、governed artifact URL、Dashboard artifact query/testing UI。

## 已實作 Components

- FastAPI app factory 與 router。
- `/healthz`、`/readyz`、`/metrics`。
- `POST /v1/tasks`。
- `GET /v1/tasks`。
- `GET /v1/tasks/{task_id}`。
- `GET /v1/tasks/{task_id}/audit`。
- `POST /v1/tasks/{task_id}/approve`。
- `GET /v1/artifacts/{artifact_id}/content`。
- `POST /v1/skills`、`GET /v1/skills`。
- SQLAlchemy ORM models。
- SQL schema 與 Alembic initial migration skeleton。
- Kafka producer/consumer wrapper。
- Worker consumer loop。
- Playwright browser runner。
- Heuristic planner。
- Evaluator。
- Local artifact store with governance metadata。
- Artifact redaction hook interface 與 default no-op implementation。
- JSON logging。
- Docker Compose local stack。
- `/demo` v0.3 Dashboard。
- Bootstrap script：schema、demo tenant/user、Kafka topics。
- API 支援 `X-Correlation-ID`。

## v0.2 行為

- Allowlisted low/medium tasks 進入 `pending_approval`。
- High/critical risk tasks 進入 `pending_approval`。
- Sensitive instructions 進入 `pending_approval`。
- Non-allowlisted domains 進入 `blocked`。
- 類 prompt-injection instructions 以 `400` 拒絕。
- Approval 將 task 移到 `queued`。
- Worker 消費 `queued` tasks，並移到 `executing`。
- Evaluation 成功時 task 變成 `completed`；較弱的 evaluation 變成 `review`。
- Execution exceptions 會讓 task 變成 `failed`，並寫入 error metadata。
- Lifecycle audit 覆蓋 created、pending approval、blocked、approved、queued、execution started、artifact written、evaluated、completed/review required、failed。

## v0.3 行為

- `ArtifactStore` protocol 定義 backend behavior。
- `LocalArtifactStore` 寫入 artifacts，並回傳 SHA-256、content type、size、backend、retention、redaction metadata。
- `NoopArtifactRedactor` 記錄 redaction hook status，但不修改 bytes。
- `TaskRunner` 持久化 artifact governance metadata，並把它放入 artifact audit payloads。
- `GET /v1/tasks/{task_id}` serialize artifact governance fields。
- `GET /v1/artifacts/{artifact_id}/content` 會檢查 tenant 與 local storage base path 後才回傳 content。
- `/demo` 顯示 artifact table、metadata JSON、preview/open links、access-check button。

## v0.3 Dashboard

`GET /demo` 可以：

- 建立 normal artifact task；
- 建立 redaction metadata task；
- 建立 high-risk 與 sensitive-instruction tasks；
- 建立 blocked-domain tasks；
- approve pending tasks；
- 顯示 recent tasks、status flow、metrics、audit、steps、evaluation、artifacts；
- 檢視 artifact content type、size、SHA、backend、redaction status、metadata；
- 從 UI 測試 artifact content access。

## 尚待實作

- Formal OIDC/JWT auth 與 RBAC。
- Request-scoped tenant/user context。
- Planner output schema validation。
- SkillHub resolver integration with planner/runner。
- Per-action confirmation。
- Redis locks/rate limiting/dedupe。
- DLQ 與 poison message replay tooling。
- Worker autoscaling。
- 完整 MinIO/S3 artifact backend。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。
- Worker metrics endpoint 或 multiprocess metrics aggregation。

## 建議下一步

以獨立 implementation slice 開始 v0.4 Planner/SkillHub integration，並讓 v0.3 artifact governance 維持穩定底座。

# Roadmap

Roadmap 以可查詢、可驗證的 implementation slice 為單位。每個版本都應有 `/demo` Dashboard 或等價 smoke test 入口。

## v0.1：可執行 Demo

目標：建立 Docker Compose stack，包含 API、worker、PostgreSQL、Kafka、Redis、Playwright，能跑基本 browser task flow。

已完成：

- `POST /v1/tasks` 建立 task。
- Worker 執行 allowlisted browser task。
- 保存 screenshot / HTML artifact。
- Evaluator 寫入結果。

## v0.2：Lifecycle、Approval、Observability Dashboard

目標：讓 task 狀態、policy decision、approval、audit、metrics 與 worker 行為可觀測。

已完成：

- allowlisted task 進入 `pending_approval`。
- high/critical risk 與敏感指令 task 需要 approval。
- non-allowlisted domain task 進入 `blocked`。
- approval 後 task 進入 `queued` 並發布 `agent.tasks.queued`。
- `/demo` 顯示 lifecycle、approval、metrics、audit、steps、evaluation、artifacts。

## v0.3：Artifact Governance 與 Dashboard Query

目標：讓 artifacts 有治理 metadata、tenant-scoped access check，以及 Dashboard 查詢/測試能力。

已完成：

- `ArtifactStore` protocol。
- `LocalArtifactStore` 保存 SHA-256、content type、size、backend、retention、redaction metadata。
- `NoopArtifactRedactor` 作為預設 redaction hook。
- `GET /v1/artifacts/{artifact_id}/content` 檢查 tenant 與 artifact base path。
- `/demo` Artifact Query panel。

## v0.4：Planner/SkillHub Integration

目標：讓 Planner output 可驗證、可 fallback、可查詢；讓 SkillHub resolver metadata 出現在 Dashboard。

已完成：

- `src/browser_agent/planner.py` Planner schema validation。
- 支援 browser actions：`goto`、`click`、`fill`、`press`、`wait`、`extract_text`、`screenshot`。
- invalid Planner output 轉為 deterministic fallback。
- Planner metadata 寫入 `tasks.metadata.planner` 與 `tasks.metadata.plan`。
- `TaskRunner` 將 browser action 對應到 SkillHub capability。
- resolver metadata 寫入 `task_steps.input_data.skill`。
- 找不到 skill 時使用 builtin browser action fallback。

## v0.5：Auth/RBAC 與 Production Approval

目標：把固定 demo identity 升級成 request-scoped authenticated actor，並用角色權限控制 production approval flow。

已完成：

- 本機 OIDC-compatible JWT。
- `ActorContext`、`require_roles()`、role permissions。
- `POST /v1/auth/demo-token` 與 `GET /v1/auth/me`。
- tenant/user/role claims。
- RBAC roles：creator、approver、operator、admin。
- task create 使用 token actor。
- approval API 使用 authenticated actor，不信任 request body `approved_by`。
- approval audit 與 Kafka queued event 保存 actor metadata。
- `/metrics` 限 operator/admin。
- `/v1/skills` create 限 admin。
- `/demo` v0.5 Identity/RBAC panel 與 forbidden scenario。

## v0.6 候選方向

以下尚未排序，可依下一個產品目標挑選：

- 外部 OIDC/JWKS verifier。
- Rate limiting / idempotency / Redis locks。
- Worker service identity。
- DLQ 與 replay tooling。
- CI pipeline。
- MinIO/S3 active artifact backend。

## v1.0：Production-Ready Platform

目標：往正式 production deployment 靠攏。

候選內容：

- Kubernetes manifests 或 Helm chart。
- Worker autoscaling。
- Redis locks、dedupe、rate limiting。
- DLQ 與 replay tooling。
- 強化 browser sandbox，例如 gVisor、Kata 或 microVM。
- secrets vault integration。
- distributed tracing。
- production Dashboard 與 alerting。
- browser replay UI。

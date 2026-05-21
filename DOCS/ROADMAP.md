# Roadmap

本 roadmap 以可交付、可測試的 implementation slice 為單位。

## v0.1：可執行 Demo

目標：建立可用的 Docker Compose stack，讓 API、worker、PostgreSQL、Kafka、Redis、Playwright 可以完成基本 browser task flow。

已完成：
- `POST /v1/tasks` 建立 task。
- Worker 執行 allowlisted browser task。
- 產生 screenshot 與 HTML artifact。
- Evaluator 寫入執行結果。

## v0.2：Lifecycle、Approval、Observability Dashboard

目標：讓 task 狀態、policy decision、approval、audit、metrics 與 worker 行為可觀測。

已完成：
- allowlisted task 進入 `pending_approval`。
- high/critical risk 與敏感指令 task 需要 approval。
- non-allowlisted domain task 進入 `blocked`。
- approval 後 task 進入 `queued` 並發布 `agent.tasks.queued`。
- worker 消費 queued task，失敗時寫入 error metadata。
- `GET /v1/tasks`、`GET /v1/tasks/{task_id}/audit`。
- `/demo` 顯示 lifecycle、approval、metrics、audit、steps、evaluation、artifacts。

## v0.3：Artifact Governance 與 Dashboard Query

目標：讓 artifacts 有治理 metadata、tenant-scoped access check，以及 Dashboard 查詢/測試能力。

已完成：
- `ArtifactStore` protocol。
- `LocalArtifactStore` 寫入 SHA-256、content type、size、backend、retention、redaction metadata。
- `NoopArtifactRedactor` 作為預設 redaction hook。
- `GET /v1/artifacts/{artifact_id}/content` 檢查 tenant 與 artifact base path。
- `/demo` Artifact Query panel 可預覽 screenshot、開啟 HTML、測試 governed artifact access。

## v0.4：Planner/SkillHub Integration

目標：讓 Planner 輸出可驗證、fallback 可稽核、SkillHub resolver 結果可查詢，並透過 Dashboard 測試。

已完成：
- `src/browser_agent/planner.py` 定義 Planner schema validation。
- 支援 action：`goto`、`click`、`fill`、`press`、`wait`、`extract_text`、`screenshot`。
- 無效 Planner output 觸發 deterministic fallback。
- Planner metadata 寫入 `tasks.metadata.planner`，實際執行步驟寫入 `tasks.metadata.plan`。
- `TaskRunner` 對每個 browser action 解析 SkillHub capability，例如 `browser.goto`。
- resolver 結果寫入 `task_steps.input_data.skill`。
- 找不到 skill 時不阻止執行，改用 builtin browser action fallback。
- `/demo` 更新為 `Browser Agent v0.4 Dashboard`，新增 Planner/SkillHub 查詢與測試情境。
- v0.4 測試結果已記錄於 [TEST_REPORT.md](./TEST_REPORT.md)。

## v0.5：Auth/RBAC 與 Production Approval

預計範圍：
- OIDC/JWT auth。
- tenant/user/role claims。
- RBAC roles：creator、approver、operator、admin。
- production human approval API 與 UI。
- approval audit 使用 authenticated actor。

## v1.0：Production-Ready Platform

預計範圍：
- Kubernetes manifests 或 Helm chart。
- Worker autoscaling。
- Redis locks、dedupe、rate limiting。
- DLQ 與 replay tooling。
- 強化 sandbox，例如 gVisor、Kata 或 microVM。
- secrets vault 與短期憑證。
- distributed tracing。
- production Dashboard 與 alerting。
- browser replay UI。

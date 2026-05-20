# Roadmap

Roadmap 依目前 scaffold 狀態切成可落地階段。每個階段都應有測試、文件與可驗證
Dashboard 或 demo。

## v0.1：本機可跑通 demo

狀態：已完成。

目標是讓本機 Docker Compose 可以跑通最短 browser task flow。`/demo` 可建立並
核准 `https://example.com` 任務，worker 可使用 Playwright 完成截圖，UI 可顯示
completed status、evaluation、screenshot 與 HTML artifact。

## v0.2：任務生命週期、核准與觀察 Dashboard

狀態：completion/stabilization 已完成本輪收尾。

v0.2 的目標是讓任務狀態、policy decision、approval、audit、metrics 與 worker
行為可以被 API、測試與 Dashboard 觀察。

已完成：

- allowlisted low/medium task 進入 `pending_approval`。
- `risk_level=high|critical` 不再永久 `blocked`，而是進入 `pending_approval`。
- sensitive instruction，例如 `login`, `password`, `payment`, `transfer`，會進入 `pending_approval`。
- 非 allowlist domain 維持 `blocked`。
- `PolicyDecision.requires_approval` 已接入 Orchestrator。
- policy reason 已寫入 task metadata 與 audit payload。
- approval 後 task 進入 `queued`，並發布 `agent.tasks.queued` event。
- worker 只執行 `queued` task。
- 成功後進入 `completed/review`，失敗後進入 `failed` 並保存 error metadata。
- 核心 metrics 已接上 create/executed/failed/duration；目前為 process-local metrics，尚未做 API/Worker 匯總。
- lifecycle audit 已覆蓋 created、pending approval、blocked、approved、queued、execution started、artifact written、evaluated、completed/review required、failed。
- 新增 `GET /v1/tasks` 供 Dashboard 顯示最近任務。
- 新增 `GET /v1/tasks/{task_id}/audit` 供 Dashboard 顯示 audit timeline。
- `/demo` 已升級為 v0.2 Dashboard，可建立多種任務情境、核准 pending 任務、查看 metrics/audit/steps/artifacts。

仍保留到後續版本：

- 正式 auth、OIDC/JWT 與 RBAC。
- 正式多租戶 request context。
- DLQ、progress events 與 replay tooling。
- per-action confirmation。
- 更完整的 production Dashboard 與 alerting。
- 跨 process metrics 匯總或 Worker metrics endpoint。

## v0.3：Artifact 與治理補強

下一步建議進入 v0.3，但不要和 v0.2 混在同一批變更裡。

目標：

- 抽象 artifact backend，保留 local backend，新增 MinIO/S3 backend。
- 補 artifact metadata：checksum、content type、size、retention metadata。
- 加入 HTML/screenshot redaction hook。
- 補 artifact access control 與 tenant-scoped read checks。
- 為 artifact 產生可治理的 access URL。

驗收：

- 每次 screenshot/html 都能從 `task_artifacts` 查到。
- artifact metadata 完整。
- redaction hook 有測試覆蓋。
- artifact 讀取不能越過 storage base path 或 tenant boundary。

## v0.4：Planner/SkillHub 整合

目標：

- 定義 Planner output JSON schema。
- SkillHub resolver 參與 tool/action selection。
- 保存 planner version 與 prompt/version metadata。
- 對每個 browser step 做 validation。
- 保留 deterministic fallback，方便測試。

## v0.5：Pilot 多租戶與正式 approval

目標：

- 導入 OIDC/JWT auth。
- 從 token claims 取得 tenant/user/role。
- 建立 RBAC：creator、approver、operator、admin。
- 提供正式 human approval API 與簡易管理 UI。
- approval audit 可追溯真實 actor。

## v1.0：Production-ready

目標：

- Kubernetes manifests / Helm chart。
- Worker autoscaling。
- Redis locks/dedupe/rate limiting。
- DLQ 與 replay tooling。
- gVisor/Kata/microVM sandbox。
- Secrets vault 與 short-lived credentials。
- Distributed tracing。
- Dashboard + alerting。
- Browser replay UI。
- Policy-as-code 與 rule version audit。

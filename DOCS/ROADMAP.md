# Roadmap

Roadmap 依目前 scaffold 狀態切成可落地階段。每階段都應有測試、文件與可驗證 demo。

## v0.1：本機可跑通 demo

目前狀態：已完成本機 demo 主流程。`/demo` 可以建立並核准 `https://example.com` 任務，worker 可完成 Playwright 截圖，UI 可顯示 completed status、evaluation、screenshot 與 HTML artifact。

目標：讓 Docker Compose 從乾淨環境啟動後，可以建立、核准、執行一個 allowlisted browser task，產出 HTML/screenshot 與 evaluation。

範圍：

- DB migration + default tenant/user seed。
- Kafka topics 初始化。
- Dockerfile 安裝 Playwright Chromium。
- 修正 approval 欄位型別問題。
- Runbook 指令全部可重現。
- API integration tests 覆蓋 task create/approve/get。

驗收：

- `docker compose up --build` 後可跑通一個 `https://example.com` 任務。
- `GET /v1/tasks/{id}` 可看到 `completed` 與 evaluation metadata。
- artifact 檔案存在於 compose volume。

## v0.2：任務生命週期與可觀測性

目標：讓任務狀態、audit、metrics 與 worker 行為可追蹤。

範圍：

- 補 `pending_approval`, `queued`, `failed` 狀態。
- 補 worker retry/backoff 與錯誤狀態更新。
- 核心流程接上 Prometheus metrics。
- audit log 覆蓋 task created/execution/evaluation。
- 補 correlation ID。

驗收：

- 任務失敗時 DB 有 `failed` 與 error message。
- `/metrics` 可看到 task created/executed/failed/duration。
- audit log 可追出單一 task 的完整 lifecycle。

## v0.3：Artifact 與治理補強

目標：artifact 從本地檔案提升為可治理資料。

範圍：

- 寫入 `task_artifacts` row。
- 支援 MinIO/S3 artifact backend。
- artifact checksum、content type、size、retention metadata。
- HTML/screenshot redaction hook。
- artifact access URL 或 signed URL。

驗收：

- 每次 screenshot/html 都能從 `task_artifacts` 查到。
- artifact URI 可在 MinIO 找到對應 object。

## v0.4：Planner/SkillHub 整合

目標：讓 task planning 從 heuristic stub 演進為結構化、可治理、可測試的 planner。

範圍：

- Planner output JSON schema。
- SkillHub resolver 參與 tool/action selection。
- Planner version 與 prompt/version metadata。
- Per-step validation。
- Planner fallback 與 deterministic tests。

驗收：

- 同一類任務可產生穩定 steps。
- 不合法 action/target 在執行前被拒絕。
- Skill 註冊後可被 planner/runner 使用。

## v0.5：Pilot 多租戶與 approval

目標：支援小規模內部 pilot。

範圍：

- OIDC/JWT auth。
- Tenant/user/role 由 token claims 決定。
- RBAC：creator、approver、operator、admin。
- 高風險任務進 pending approval。
- Human approval API 與簡易管理 UI。

驗收：

- 不同 tenant 看不到彼此 task。
- 高風險任務未核准不會執行。
- approval audit 可追溯 actor。

## v1.0：Production-ready

目標：可上 production 的受控 Browser Agent 執行平台。

範圍：

- Kubernetes manifests / Helm chart。
- Worker autoscaling。
- Redis locks/dedupe/rate limiting。
- DLQ 與 replay tooling。
- gVisor/Kata/microVM sandbox。
- Secrets vault 與 short-lived credentials。
- Distributed tracing。
- Dashboard + alerting。
- Browser replay UI。
- Policy-as-code 與治理審批。

驗收：

- 可水平擴充 worker。
- 任務完整可追溯。
- 高風險誤執行為 0。
- policy、planner、evaluator、artifact 都有版本與 audit trail。

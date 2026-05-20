# Roadmap

本 roadmap 描述 BrowserAgent scaffold 的 implementation slices。

## v0.1：本機可執行 Demo

目標：讓 Docker Compose 跑通最短 browser task flow。

已實作：

- API 與 worker containers。
- Postgres/Kafka/Redis/MinIO services。
- 透過 Playwright 執行 example task。
- Completed status、evaluation、screenshot、HTML artifact。

## v0.2：Lifecycle、Approval、Observability Dashboard

目標：讓 task state、policy decisions、approval、audit、metrics、worker behavior 可以透過 API、tests、Dashboard 觀察。

已實作：

- allowlisted low/medium tasks 進入 pending approval；
- high/critical risk tasks 進入 pending approval；
- sensitive instructions 進入 pending approval；
- non-allowlisted domains 進入 blocked status；
- policy reason 存入 task metadata 與 audit payloads；
- approval 將 task 移到 `queued` 並 publish `agent.tasks.queued`；
- worker consume queued tasks；
- failed execution 寫入 error metadata；
- process-local metrics；
- lifecycle audit events；
- `GET /v1/tasks`；
- `GET /v1/tasks/{task_id}/audit`；
- `/demo` Dashboard 支援 task creation、approval、metrics、audit、steps、evaluation、artifacts。

## v0.3：Artifact Governance 與 Dashboard Query

目標：讓 artifacts 能被 governance、inspection、testing，並能透過 API 與 Dashboard 驗證。

已實作：

- artifact backend abstraction；
- local artifact backend 保留為 active backend；
- S3 backend placeholder 預留給未來 deployment slice；
- artifact metadata：checksum、content type、size、backend、retention metadata、redaction metadata；
- no-op HTML/screenshot redaction hook；
- tenant-scoped artifact read checks；
- local artifact content 的 base-path enforcement；
- governed artifact access URL；
- `/demo` v0.3 Dashboard artifact table 與 Artifact Query panel；
- v0.3 unit、integration、Docker、Dashboard tests。

Acceptance status：passed。請見 [TEST_REPORT.md](./TEST_REPORT.md)。

## v0.4：Planner/SkillHub Integration

建議下一個 slice。

規劃項目：

- 定義 Planner output JSON schema；
- runner execution 前 validate planner output；
- 將 SkillHub resolver 接到 tool/action selection；
- 儲存 planner version 與 prompt/version metadata；
- 當 planner output invalid 時提供 deterministic fallback；
- 保留 v0.3 產生的 artifact governance metadata。

## v0.5：Auth/RBAC 與 Production Approval

規劃項目：

- OIDC/JWT auth；
- tenant/user/role claims；
- RBAC roles，例如 creator、approver、operator、admin；
- production human approval API 與 UI；
- approval audit 使用 authenticated actor。

## v1.0：Production-Ready Platform

規劃項目：

- Kubernetes manifests / Helm chart；
- worker autoscaling；
- Redis locks/dedupe/rate limiting；
- DLQ 與 replay tooling；
- gVisor/Kata/microVM sandbox；
- secrets vault 與 short-lived credentials；
- distributed tracing；
- Dashboard + alerting；
- browser replay UI；
- policy-as-code 與 rule version audit。

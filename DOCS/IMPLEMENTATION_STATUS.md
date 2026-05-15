# 實作狀態

此文件用來避免文件或對外說明高估目前系統成熟度。

## 已實作

- FastAPI app factory 與 router。
- `/healthz`, `/readyz`, `/metrics`。
- 建立 task：`POST /v1/tasks`。
- 讀取 task：`GET /v1/tasks/{task_id}`。
- 核准 task：`POST /v1/tasks/{task_id}/approve`。
- 註冊/list skills：`POST /v1/skills`, `GET /v1/skills`。
- SQLAlchemy ORM models。
- SQL schema 與 Alembic initial migration。
- Kafka producer/consumer wrapper。
- worker consumer loop。
- Playwright browser runner 基本 action。
- Heuristic planner。
- Evaluator 簡化評分。
- Local artifact store。
- JSON logging。
- Docker Compose local stack。
- policy/evaluator minimal tests。
- v0.1 `/demo` 本機 demo console。
- `task_artifacts` artifact 摘要回傳與安全內容讀取 endpoint。
- bootstrap script 建立 schema、seed demo tenant/user，並可建立 Kafka topics。

## 部分實作

| 能力 | 目前狀態 | 差距 |
|---|---|---|
| Task lifecycle | 有 created/blocked/approved/executing/completed/review | 沒有完整 planned/queued/verifying/failed/cancelled |
| Approval | API 與 audit 已有 | 高風險任務不會進 pending approval；欄位型別需修 |
| SkillHub | 可註冊/解析 | Planner/runner 尚未使用 SkillHub 做 tool selection |
| Artifact | 寫本地檔並寫入 `task_artifacts` | 不使用 MinIO |
| Metrics | endpoint 與 metric definitions | 核心流程未更新 metrics |
| Policy | hardcoded rules | 無 declarative policy、版本、審計 rule ID |
| Worker | 可消費 approved task | 無 retry/backoff/DLQ/progress events |
| Sandbox | Playwright in container，Dockerfile 會安裝 Chromium | 無 gVisor/Kata/microVM |
| Multi-tenant | schema 有 tenant | API 使用固定 tenant/user，無 auth context |

## 尚未實作

- Human-in-the-loop UI。
- SSO/OIDC/JWT auth。
- RBAC 與租戶隔離 middleware。
- 真正 LLM planner。
- Planner output schema validation。
- Per-action policy/confirmation。
- Redis locks、rate limiting、dedupe。
- DLQ 與 poison message handling。
- Worker autoscaling。
- MinIO/S3 artifact upload。
- Artifact retention/redaction。
- Browser session replay UI。
- Kubernetes manifests。
- CI pipeline。
- Production secret management。
- Distributed tracing。

## 目前最可能阻塞 demo 的問題

1. Worker 只執行 approved task；只建立 task 不會跑。
2. Docker Compose 需要 Kafka/Postgres ready；bootstrap 已重試，但首次 build 仍取決於本機 Docker 資源。
3. v0.1 只支援 low-risk allowlisted demo；high/critical approval flow 尚未重設計。

## 建議優先修正順序

1. 修正 seed/init 流程與 README/runbook 指令。
2. 修正 approval 欄位型別與 API contract。
3. 讓 Dockerfile 的 Playwright Chromium 安裝維持可 cache、可重現。
4. 補 API integration tests。
5. 擴充 artifact retention、content length 與 tenant access control。
6. 補 metrics increment/observe。
7. 建立 pending approval 狀態與 high-risk flow。

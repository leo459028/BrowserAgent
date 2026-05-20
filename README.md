# Enterprise Browser Agent Platform

這是一個 Browser Agent 平台的 production-grade scaffold，核心組成包含：

- FastAPI control plane
- PostgreSQL system of record
- Kafka event bus
- Redis locks / short-lived state / rate limiting hooks
- Playwright sandbox execution
- Evaluator result verification
- SkillHub versioned capability registration
- Audit trail 與 artifact storage
- Policy engine，用於 domain / action / risk gating
- v0.3 artifact governance 與本機 Dashboard 測試 UI

## 已包含

- Task lifecycle API
- Skill registry API
- Approval gate
- Kafka-based orchestration
- Browser runner worker
- Artifact persistence
- v0.2 lifecycle observability：pending approval、queued execution、failed task metadata、correlation IDs、metrics、audit coverage、本機 Dashboard 支援
- v0.2 approval policy flow：high-risk 與 sensitive tasks
- v0.3 artifact governance：local backend metadata、no-op redaction hook、tenant access checks、Dashboard artifact query/testing
- SQL schema 與 Alembic migration skeleton
- Dockerized local stack
- Automated tests

## 尚未包含

- LLM provider integration 目前只保留 interface。
- Production human-in-the-loop UI 與 auth/RBAC 尚未實作；本機 v0.3 Dashboard 只用於測試與觀察。
- Kubernetes manifests 尚未提供。
- MinIO/S3 artifact upload 尚未啟用；MinIO 目前只是 Compose 中的預留服務。

## 架構

```text
Client -> FastAPI -> Postgres
                  -> Kafka -> Worker -> Playwright sandbox -> Evaluator -> Postgres / Artifacts
                  -> Redis for future locks and ephemeral state
```

## 快速開始

### 1. 複製環境設定

```bash
cp .env.example .env
```

### 2. 啟動 Stack

```bash
docker compose up -d --build
```

### 3. 開啟 Dashboard

```text
http://localhost:8000/demo
```

使用 v0.3 Dashboard 可以建立 normal artifact、redaction metadata、high-risk、sensitive-instruction、blocked-domain tasks。Dashboard 可 approve `pending_approval` tasks，並顯示 task status、policy reason、metrics、audit timeline、evaluation result、browser steps、screenshot preview、HTML artifact links、artifact metadata 與 artifact access checks。

### 4. 手動建立 Task

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Capture example",
    "instructions":"Open the allowlisted site and capture a screenshot.",
    "priority":1,
    "risk_level":"low",
    "metadata":{
      "domains":["example.com"],
      "start_url":"https://example.com",
      "expected_domain":"example.com"
    }
  }'
```

### 5. Approve Task

```bash
curl -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"ops@example.com","note":"Approved for local v0.3 test"}'
```

### 6. 執行測試

```bash
pytest -q
docker compose exec -T api pytest -q
```

目前預期結果：`24 passed`。

## Services

| Service | 用途 |
|---|---|
| api | Control plane、task API、artifact API、v0.3 Dashboard |
| worker | 消費 Kafka events 並執行 browser tasks |
| postgres | System of record |
| redis | 預留給 locks、dedupe、short-lived state |
| kafka | Event stream |
| minio | 預留 object storage；目前 artifact backend 是 local filesystem |

## 專案結構

```text
src/browser_agent/
  api.py
  app.py
  db.py
  models.py
  schemas.py
  policy.py
  kafka.py
  storage.py
  evaluator.py
  skillhub.py
  orchestrator.py
  services/
worker/
alembic/
sql/
tests/
DOCS/
```

## 文件

建議先閱讀：

- [DOCS/IMPLEMENTATION_STATUS.md](DOCS/IMPLEMENTATION_STATUS.md)
- [DOCS/API.md](DOCS/API.md)
- [DOCS/RUNBOOK.md](DOCS/RUNBOOK.md)
- [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)
- [DOCS/ROADMAP.md](DOCS/ROADMAP.md)

## Production Notes

### Security

- 使用 per-tenant allowlists。
- Secrets 應放在 vault，不應放在 Postgres。
- Browser sessions 應保持 ephemeral。
- Login/payment flows 應由 policy 要求 approval 或 hard-block。
- High-risk actions 必須 approval。
- Demo tenant/user UUIDs 之後要改為 auth/RBAC claims。

### Reliability

- Task events 應維持 idempotent。
- Task execution 目前只有 minimal retry support。
- DLQ/replay tooling 尚未實作。
- Evaluator 與 execution 已解耦。

### Observability

- Structured JSON logs
- Health endpoints
- Metrics endpoint
- Task-level audit trail
- v0.3 Dashboard artifact inspection

## 建議下一步

1. 實作 v0.4 Planner output schema validation 與 SkillHub resolver integration。
2. 加入 SSO/OIDC 與 RBAC。
3. 加入 production approval UI。
4. 實作真正的 MinIO/S3 artifact backend。
5. 加入 K8s manifests、HPA 與 production observability。

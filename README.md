# BrowserAgent

## 一般版

BrowserAgent 是一個受控的瀏覽器自動化平台雛形。它可以建立任務、等待人工核准、交給 worker 操作瀏覽器、保存 screenshot / HTML artifacts，並把重要事件寫進 audit log，讓任務結果可以查詢與追溯。

目前版本是 **v0.6：Reliability Foundation**。這版承接 v0.5 Auth/RBAC 與 Production Approval，新增 task create idempotency、rate limiting、worker service identity、task lock、DLQ metadata 與 replay API，讓本機 demo 更接近 production reliability 的基本骨架。

### v0.6 目前可以展示

- `/demo` Dashboard 可以切換 creator、approver、operator、admin 角色。
- `/demo` Reliability / DLQ panel 可以查 reliability store、rate limit、worker identity、DLQ topic，並測試 Idempotency smoke。
- creator / admin 可以建立 task。
- `POST /v1/tasks` 可使用 `Idempotency-Key` header，同 key 同 payload 會回同一個 task，不會重複發布 created event。
- task create 會依 tenant/user 做每分鐘 rate limit，超過時回 `429`。
- approver / admin 可以核准 `pending_approval` task。
- operator / admin 可以讀 `/metrics`。
- audit 與 approval 會記錄 token actor，例如 `approver@example.com`。
- worker audit actor 會使用 `service:<WORKER_SERVICE_ID>`，並用 reliability lock 避免同一 task 重複執行。
- worker 最終失敗會寫入 `tasks.metadata.reliability.dlq`，發布 `agent.tasks.dlq`，operator/admin 可查詢並 replay 回 `queued`。
- 錯誤角色會被 API 擋下並回傳 `403`。
- task 執行後仍可查 Planner validation、SkillHub resolution、steps、evaluation、artifacts。
- Artifact content 讀取會用 token tenant 做 access check。

### 仍然不是正式生產產品

v0.6 仍是 production-grade scaffold，不是完整 production deployment。它尚未接真實外部 OIDC/JWKS、Kubernetes、MinIO/S3 active artifact backend、secrets vault、分散式 tracing、production operator UI 或更強的 browser sandbox。

### 適合場景

- 驗證「瀏覽器自動化 + 人工核准 + audit」的產品流程。
- 做企業內部 Browser Agent 平台原型。
- 測試 task lifecycle、Planner fallback、SkillHub metadata、artifact governance。
- 驗證 RBAC 權限邊界是否能控制建立、核准、查詢與營運觀測。

### 不適合場景

- 直接上正式生產環境。
- 處理付款、轉帳、帳戶修改、法律文件提交等高風險操作。
- 大量爬取、繞過網站限制或規避驗證。
- 取代完整 QA 自動化平台或 production SSO/IdP 系統。

## 技術版

### 目前能力

- FastAPI control plane：auth、task、approval、artifact、skill API。
- 本機 JWT auth：HS256 token，claims 包含 `iss`、`aud`、`sub`、`tenant_id`、`email`、`roles`、`exp`。
- RBAC roles：`creator`、`approver`、`operator`、`admin`。
- PostgreSQL system of record：tenants、users、tasks、steps、artifacts、evaluations、approvals、audit logs。
- Kafka event bus：task created / queued event。
- Reliability foundation：memory/Redis-backed rate limit、idempotency 查詢、worker lock、DLQ metadata 與 replay。
- CI：GitHub Actions 執行 pytest、compileall、diff whitespace check。
- Worker + Playwright runner：執行 `goto`、`click`、`fill`、`press`、`wait`、`extract_text`、`screenshot`。
- Planner 仍是 `heuristic-v0.4`：schema validation 與 deterministic fallback。
- SkillHub v0.4 metadata：解析 `browser.<action>` capability，不執行第三方 skill。
- Local artifact governance：SHA-256、content type、size、retention、redaction metadata、tenant access check。
- `/demo` v0.6 Dashboard：Reliability/DLQ、Identity/RBAC、production approval、metrics、audit、Planner/SkillHub、artifacts。

### 快速啟動

```powershell
cp .env.example .env
docker compose up -d --build
```

Dashboard：

```text
http://localhost:8000/demo
```

Health check：

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

### 取得 Demo Token

```powershell
$token = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"creator"}'
```

可用 role：

- `creator`
- `approver`
- `operator`
- `admin`

### 建立 Task

```powershell
$creator = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"creator"}'

curl.exe -X POST http://localhost:8000/v1/tasks `
  -H "Authorization: Bearer $($creator.access_token)" `
  -H "Content-Type: application/json" `
  -H "Idempotency-Key: capture-example-001" `
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

### 核准 Task

```powershell
$approver = Invoke-RestMethod -Method Post `
  -Uri http://localhost:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"approver"}'

curl.exe -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve `
  -H "Authorization: Bearer $($approver.access_token)" `
  -H "Content-Type: application/json" `
  -d '{"note":"Approved from v0.6 local smoke test"}'
```

`approved_by` request 欄位已不再是信任來源；API 會使用 Bearer token 裡的 actor email 寫入 approval 與 audit。

### 本機測試

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker 可用時：

```powershell
docker compose exec -T api pytest -q
```

實際驗證結果請見 [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)。

### 文件

- [DOCS/OVERVIEW.md](DOCS/OVERVIEW.md)
- [DOCS/API.md](DOCS/API.md)
- [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)
- [DOCS/DATA_MODEL.md](DOCS/DATA_MODEL.md)
- [DOCS/SECURITY_AND_POLICY.md](DOCS/SECURITY_AND_POLICY.md)
- [DOCS/RUNBOOK.md](DOCS/RUNBOOK.md)
- [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)

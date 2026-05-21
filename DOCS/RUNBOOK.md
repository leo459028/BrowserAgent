# Runbook

本 runbook 說明如何在本機 Docker Compose 驗證 v0.4 Dashboard、Planner/SkillHub、artifact governance 與 E2E flow。Production 仍需要正式 auth/RBAC、secret management、object storage backend、retry/DLQ hardening 與更強的 browser sandbox isolation。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
```

`api` 與 `worker` services 啟動時會先執行 `python scripts/bootstrap.py`。Bootstrap 會：

- 建立 SQLAlchemy schema。
- seed demo tenant/user。
- 建立 Kafka topics：`agent.tasks.created`、`agent.tasks.queued`、`agent.tasks.failed`、`agent.tasks.completed`。

檢查 service status：

```powershell
docker compose ps
```

檢查 API：

```powershell
curl.exe http://127.0.0.1:8000/healthz
curl.exe http://127.0.0.1:8000/readyz
curl.exe http://127.0.0.1:8000/metrics
```

預期：

```json
{"status":"ok"}
{"status":"ready"}
```

## 2. 開啟 v0.4 Dashboard

```text
http://127.0.0.1:8000/demo
```

Dashboard scenarios：

- `Normal planner task`：預期先進入 `pending_approval`，approval 後 queued，由 worker 執行並產生 screenshot/html artifacts。
- `Fallback planner task`：預期 invalid Planner output 被記錄，並使用 deterministic fallback plan。
- `SkillHub resolved task`：先按 `Register demo skills`，再建立 task，預期 `browser.goto` 與 `browser.screenshot` resolved。
- `SkillHub missing task`：未註冊對應 skill 時，預期繼續使用 builtin browser action fallback。
- `Redaction metadata task`：預期 artifacts 具備 redaction metadata。
- `High-risk task`：預期 `pending_approval`，並有 high-risk policy reason。
- `Sensitive instruction task`：預期 `pending_approval`，並有 sensitive-action policy reason。
- `Blocked-domain task`：預期 `blocked`。

正常 allowlisted low-risk task 顯示 `pending_approval` 是預期行為；Planner metadata 會在 approval 後由 worker 執行時才出現。

## 3. 測試命令

Host：

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker：

```powershell
docker compose exec -T api pytest -q
```

目前預期 `pytest -q` 與 container pytest 都是 `31 passed`。

## 4. Normal Planner API E2E

建立 allowlisted task：

```powershell
$body = @{
  title = "Capture example"
  instructions = "Open the allowlisted site and capture a screenshot."
  priority = 1
  risk_level = "low"
  metadata = @{
    domains = @("example.com")
    start_url = "https://example.com"
    expected_domain = "example.com"
  }
} | ConvertTo-Json -Depth 5

$created = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/tasks `
  -ContentType "application/json" `
  -Body $body
```

Approve：

```powershell
$approval = @{ approved_by = "ops@example.com"; note = "local v0.4 test" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/v1/tasks/$($created.task_id)/approve" `
  -ContentType "application/json" `
  -Body $approval
```

查詢 task：

```powershell
Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/tasks/$($created.task_id)"
```

預期：

- final status：`completed`。
- `metadata.planner.valid=true`。
- `metadata.planner.fallback_used=false`。
- `steps` 有 `goto` 與 `screenshot`。
- artifacts 有 `screenshot` 與 `html`。
- evaluation verdict 是 `pass`。

## 5. Fallback Planner E2E

在 task metadata 加入：

```json
{"planner_test": "invalid"}
```

預期：

- final status：`completed`。
- `metadata.planner.valid=false`。
- `metadata.planner.fallback_used=true`。
- `metadata.planner.validation_errors` 有錯誤摘要。
- `metadata.plan` 是 `goto,screenshot`。
- audit timeline 有 `task.plan_fallback_used`。

## 6. Artifact Content

取得 artifact content：

```powershell
curl.exe http://127.0.0.1:8000/v1/artifacts/<ARTIFACT_ID>/content
```

預期：

- screenshot endpoint 回傳 `200 image/png`。
- HTML endpoint 回傳 `200 text/html; charset=utf-8`。
- tenant mismatch 或 path traversal 回傳 `403`。
- missing file 回傳 `404`。

## 7. Kafka Topics

列出 topics：

```powershell
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

預期 topics：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

## 8. Troubleshooting

### `/readyz` 失敗

```powershell
docker compose ps
docker compose logs postgres
docker compose exec postgres pg_isready -U agent -d agent
```

### API bootstrap 等不到 Kafka

若 Kafka log 出現 stale broker session，例如 `NodeExistsException`，先不刪 volume，重啟相關服務：

```powershell
docker compose restart zookeeper kafka api worker
```

### `POST /v1/tasks` 出現 foreign key errors

重新執行 bootstrap：

```powershell
docker compose exec api python scripts/bootstrap.py
```

### Task 卡在 `queued`

檢查 approval、Kafka、worker：

```powershell
docker compose logs worker
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
curl.exe http://127.0.0.1:8000/v1/tasks/<TASK_ID>
```

### Artifact content 回傳 `403 outside artifact storage`

確認目前呼叫的是寫入 artifact 的同一個 API process。如果 local uvicorn 與 Docker 都使用 port `8000`，測試 Docker 前請先停止 local uvicorn。

### Worker Playwright failure

重新 build image：

```powershell
docker compose build --no-cache api worker
```

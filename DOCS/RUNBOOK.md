# Runbook

本 runbook 說明如何在本機 Docker Compose 驗證 v0.6 Reliability Foundation、Auth/RBAC、Production Approval、Planner/SkillHub、artifact governance 與 E2E flow。Production 仍需要外部 OIDC/JWKS、secret management、object storage backend、production DLQ operations 與更強的 browser sandbox isolation。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
```

`api` 與 `worker` services 啟動時會執行：

- 建立 SQLAlchemy schema。
- seed demo tenant/users。
- 建立 Kafka topics。

檢查 service status：

```powershell
docker compose ps
```

檢查 API：

```powershell
curl.exe http://127.0.0.1:8000/healthz
curl.exe http://127.0.0.1:8000/readyz
```

預期：

```json
{"status":"ok"}
{"status":"ready"}
```

## 2. 開啟 v0.6 Dashboard

```text
http://127.0.0.1:8000/demo
```

Dashboard scenarios：

- `Reliability / DLQ`：查 reliability store、rate limit、worker identity、DLQ topic。
- `Idempotency smoke`：預期同 key 同 payload replay 同一個 task。
- `Refresh DLQ`：查 failed tasks；若有 DLQ task，可 replay 回 `queued`。
- `Identity / RBAC`：切換 role、查看 token actor 與 permissions。
- `Try operator create`：預期顯示 `403`，因 operator 不可建立 task。
- `Normal planner task`：creator 建立，approver 核准，worker 完成，產生 screenshot/html artifacts。
- `Fallback planner task`：invalid Planner output 轉 deterministic fallback。
- `SkillHub resolved task`：先按 `Register demo skills`，再建立 task，預期 `browser.goto` 與 `browser.screenshot` resolved。
- `SkillHub missing task`：未註冊對應 skill 時，預期使用 builtin browser action fallback。
- `High-risk task`：預期 `pending_approval`，policy reason 是 high-risk。
- `Sensitive instruction task`：預期 `pending_approval`，policy reason 是 sensitive-action。
- `Blocked-domain task`：預期 `blocked`。

正常 allowlisted low-risk task 顯示 `pending_approval` 是預期行為；Planner metadata 會在 approval 後由 worker 執行時才出現。

## 3. Auth Smoke Test

取得 creator token：

```powershell
$creator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"creator"}'
```

確認 actor：

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/auth/me `
  -Headers @{ Authorization = "Bearer $($creator.access_token)" }
```

預期 `email=creator@example.com`，roles 包含 `creator`。

## 4. Normal Planner API E2E

建立 task：

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
  -Headers @{
    Authorization = "Bearer $($creator.access_token)"
    "Idempotency-Key" = "runbook-normal-001"
  } `
  -ContentType "application/json" `
  -Body $body
```

Approve：

```powershell
$approver = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"approver"}'

$approval = @{ note = "local v0.6 test" } | ConvertTo-Json
Invoke-RestMethod -Method Post `
  -Uri "http://127.0.0.1:8000/v1/tasks/$($created.task_id)/approve" `
  -Headers @{ Authorization = "Bearer $($approver.access_token)" } `
  -ContentType "application/json" `
  -Body $approval
```

查詢 task：

```powershell
$operator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/demo-token `
  -ContentType "application/json" `
  -Body '{"role":"operator"}'

Invoke-RestMethod -Method Get `
  -Uri "http://127.0.0.1:8000/v1/tasks/$($created.task_id)" `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

預期：

- final status：`completed`。
- `metadata.planner.valid=true`。
- `metadata.planner.fallback_used=false`。
- `steps` 包含 `goto` 與 `screenshot`。
- artifacts 包含 `screenshot` 與 `html`。
- evaluation verdict 為 `pass`。

## 5. RBAC Regression

Operator 建立 task 應回 `403`：

```powershell
Invoke-WebRequest -Method Post `
  -Uri http://127.0.0.1:8000/v1/tasks `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" } `
  -ContentType "application/json" `
  -Body $body
```

Creator approve task 應回 `403`。

## 6. Reliability / DLQ Smoke

查 reliability status：

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/reliability `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

預期可看到 `store.backend=redis`、`worker_service_id`、`dlq_topic=agent.tasks.dlq`。

Idempotency replay：

```powershell
$headers = @{
  Authorization = "Bearer $($creator.access_token)"
  "Idempotency-Key" = "runbook-idempotency-001"
}
$first = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $headers -ContentType "application/json" -Body $body
$second = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers $headers -ContentType "application/json" -Body $body
```

預期 `$first.task_id` 等於 `$second.task_id`，且 `$second.idempotency.replayed=true`。

查 DLQ：

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/dlq/tasks `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

若有 failed DLQ task，可用 `POST /v1/dlq/tasks/<TASK_ID>/replay` replay 回 `queued`。

## 7. Artifact Content

讀取 artifact content：

```powershell
curl.exe http://127.0.0.1:8000/v1/artifacts/<ARTIFACT_ID>/content `
  -H "Authorization: Bearer <TOKEN>"
```

預期：

- screenshot endpoint 回 `200 image/png`。
- HTML endpoint 回 `200 text/html; charset=utf-8`。
- tenant mismatch 或 path traversal 回 `403`。
- missing file 回 `404`。

## 8. 測試命令

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

目前 host pytest 預期為 `47 passed`；最新實測請看 [TEST_REPORT.md](./TEST_REPORT.md)。

## 9. Troubleshooting

### `/readyz` 失敗

```powershell
docker compose ps
docker compose logs postgres
docker compose exec postgres pg_isready -U agent -d agent
```

### API bootstrap 等 Kafka

若 Kafka log 顯示 stale broker session，例如 `NodeExistsException`，可先嘗試：

```powershell
docker compose restart zookeeper kafka api worker
```

### `401 Unauthorized`

確認有帶：

```text
Authorization: Bearer <JWT>
```

或重新呼叫 `/v1/auth/demo-token` 取得 token。

### `403 insufficient role`

確認 role 是否符合 endpoint：

- 建立 task：creator/admin。
- 核准 task：approver/admin。
- metrics：operator/admin。
- 建立 skill：admin。

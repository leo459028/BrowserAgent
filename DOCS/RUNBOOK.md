# Runbook

本 runbook 說明如何在本機 Docker Compose 驗證 V1.0 Operations Center。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
```

檢查：

```powershell
docker compose ps
curl.exe http://127.0.0.1:8000/healthz
curl.exe http://127.0.0.1:8000/readyz
```

## 2. 開啟 Operations Center

```text
http://127.0.0.1:8000/operations
```

應看到：

- `Browser Agent v1.0 Operations Center`
- `Operations Readiness`
- `Artifact Backend`
- `Reliability / DLQ`
- `Replay Timeline`

## 3. Auth Smoke

```powershell
$operator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"operator"}'

Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/auth/me `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

## 4. Operations Readiness

```powershell
Invoke-RestMethod -Method Get `
  -Uri http://127.0.0.1:8000/v1/ops/readiness `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" }
```

Docker Compose 預期 artifact backend 為 `s3`，reliability backend 為 `redis`。

## 5. Normal Task E2E

在 `/operations` 選 `Normal planner task`，按 `Create task`，再按 `Approve selected`。預期 final status 為 `completed`，artifacts 包含 screenshot/html，Replay Timeline 有 audit、steps、artifacts、evaluation。

## 6. DLQ Operations

- `Refresh DLQ`：查 failed DLQ tasks。
- 單筆 `replay`：把 failed task 放回 `queued`。
- `Bulk DLQ replay`：批次 replay non-quarantined tasks。
- Quarantine API：

```powershell
Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/dlq/tasks/<TASK_ID>/quarantine `
  -Headers @{ Authorization = "Bearer $($operator.access_token)" } `
  -ContentType "application/json" `
  -Body '{"reason":"poison message"}'
```

## 7. 測試命令

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
docker compose exec -T api pytest -q
```

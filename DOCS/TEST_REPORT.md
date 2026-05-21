# Test Report

最後更新：2026-05-21

## 摘要

v0.5 Auth/RBAC 與 Production Approval 實作後，已完成 host 端 pytest、compileall、diff check、Docker Compose build/start、container pytest，以及 Docker API/Dashboard/RBAC/worker/artifact smoke test。

本次測試確認：

- API 預設需要 Bearer token。
- invalid/missing/expired token 回 `401`。
- wrong role 回 `403`。
- creator 可建立 task。
- approver 可核准 task，audit actor 為 `approver@example.com`。
- operator 可讀 metrics，不可建立 task。
- admin 可註冊 SkillHub skill。
- artifact content endpoint 使用 token tenant 做 access check。
- `/demo` 顯示 `Browser Agent v0.5 Dashboard` 與 `Identity / RBAC` panel。

## Host 測試結果

日期：2026-05-21

### `pytest -q`

結果：

```text
39 passed, 2 warnings in 1.92s
```

Warnings：

- `pythonjsonlogger.jsonlogger` deprecation warning。
- `.pytest_cache` 寫入 permission warning：測試結果通過，但 sandbox 無法寫入部分 pytest cache 檔案。

### `python -m compileall src tests worker alembic`

結果：

```text
exit code 0
```

輸出顯示 `src`、`tests`、`worker`、`alembic` 皆完成 compile scan，未發現語法錯誤。

### `git diff --check`

結果：

```text
exit code 0
```

表示目前 diff 沒有 trailing whitespace 或 patch 格式問題。

## v0.5 Test Coverage

### `tests/test_v05_auth_rbac.py`

覆蓋：

- missing token、invalid token、expired token 回 `401`。
- operator 建立 task 回 `403`。
- `/v1/auth/demo-token` 與 `/v1/auth/me` 回傳 actor 與 permissions。
- creator 建立 task 時，`tenant_id` 與 `created_by` 來自 token actor。
- creator 不可 approve；approver 可 approve。
- approval row、audit payload、Kafka queued event 使用 authenticated actor。
- operator 可讀 `/metrics`；creator 讀 `/metrics` 回 `403`。
- admin 可註冊 SkillHub skill。
- artifact content 使用 token tenant 做 access check，tenant mismatch 回 `403`。

### Updated regression tests

- `tests/test_v01_demo.py` 已更新為 v0.5 Dashboard rendering，並在 task list / audit API 測試中使用 Bearer token。
- v0.1-v0.4 既有 tests 維持通過。

## Docker 驗證

日期：2026-05-21

### Docker availability

第一次在 sandbox 內執行 `docker info` 因 Docker API permission 被擋：

```text
permission denied while trying to connect to the docker API
```

改用核准後的 Docker daemon access 執行成功：

```text
Server Version: 29.4.1
Operating System: Docker Desktop
OSType: linux
```

### `docker compose up -d --build`

結果：

```text
Image browseragent-api Built
Image browseragent-worker Built
Container browseragent-postgres-1 Started
Container browseragent-redis-1 Started
Container browseragent-kafka-1 Started
Container browseragent-api-1 Started
Container browseragent-worker-1 Started
```

Build log 確認 `PyJWT-2.12.1` 已安裝進 container image。

### Bootstrap 問題與修正

Docker 驗證第一次發現 `api` service 退出，原因是 API 與 worker 同時執行 `scripts/bootstrap.py`，新增多個 demo users 時發生 duplicate key race：

```text
psycopg.errors.UniqueViolation: duplicate key value violates unique constraint "users_pkey"
```

修正方式：

- `scripts/bootstrap.py` 改用 PostgreSQL `INSERT ... ON CONFLICT` upsert seed demo tenant/users。

第二次啟動又發現既有 Docker volume 的 `created_at` 欄位是 NOT NULL 且沒有 database-level default：

```text
psycopg.errors.NotNullViolation: null value in column "created_at" of relation "tenants"
```

修正方式：

- upsert tenant/users 時明確提供 `created_at` timestamp。

修正後重新執行：

```text
docker compose up -d --build -> exit code 0
```

### `docker compose exec -T api pytest -q`

結果：

```text
39 passed in 1.68s
```

## Docker API / Dashboard / RBAC Smoke

執行項目：

- `GET /healthz`
- `GET /readyz`
- `POST /v1/auth/demo-token` for creator / approver / operator / admin
- `GET /v1/auth/me` with operator token
- `GET /demo`
- `GET /metrics` with operator token
- operator `POST /v1/tasks` forbidden check
- creator `POST /v1/tasks`
- approver `POST /v1/tasks/{task_id}/approve`
- polling operator `GET /v1/tasks/{task_id}`
- operator `GET /v1/tasks/{task_id}/audit`
- operator `GET /v1/artifacts/{artifact_id}/content`

結果：

```json
{
  "health": "ok",
  "ready": "ready",
  "dashboardV05": true,
  "identityPanel": true,
  "operatorEmail": "operator@example.com",
  "metricsStatus": 200,
  "forbiddenCreateStatus": 403,
  "createdStatus": "pending_approval",
  "approvedStatus": "queued",
  "finalStatus": "completed",
  "plannerValid": true,
  "fallbackUsed": false,
  "artifactCount": 2,
  "artifactStatus": 200,
  "artifactContentType": "image/png",
  "approvalActor": "approver@example.com"
}
```

## Dashboard 驗證結果

HTTP 驗證：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/demo
```

頁面文字檢查結果：

```text
PASS Browser Agent v0.5 Dashboard
PASS Identity / RBAC
PASS production approval
PASS Planner
PASS SkillHub
PASS Artifact Query
```

Dashboard artifact preview 在 v0.5 會透過 JS fetch 帶 operator token 讀取 content endpoint；直接用 `<img src="/v1/artifacts/...">` 已不再適用，因為 artifact endpoint 需要 Bearer token。

## 文件同步檢查

已同步更新：

- `README.md`
- `DOCS/OVERVIEW.md`
- `DOCS/API.md`
- `DOCS/ARCHITECTURE.md`
- `DOCS/CONFIGURATION.md`
- `DOCS/DATA_MODEL.md`
- `DOCS/DEVELOPMENT.md`
- `DOCS/IMPLEMENTATION_STATUS.md`
- `DOCS/OBSERVABILITY.md`
- `DOCS/ROADMAP.md`
- `DOCS/RUNBOOK.md`
- `DOCS/SECURITY_AND_POLICY.md`
- `DOCS/TEST_REPORT.md`
- `DOCS/USE_CASES.md`

文件已更新為 v0.5 Auth/RBAC、production approval、demo JWT、role permissions、Dashboard v0.5 與測試數量。

## 其他觀察

- Host 端 pytest 仍有 `.pytest_cache` permission warning，測試結果不受影響。
- Docker Compose stack 使用既有 volumes；本次修正讓 bootstrap 在重複與並行執行時可安全 upsert demo tenant/users。
- v0.5 仍未接外部 OIDC/JWKS；目前 JWT 是 local scaffold。

## AGENTS.md 文件保留規範更新

日期：2026-05-21

本次依使用者要求更新根目錄 `AGENTS.md`，新增文件維護規範：更新全部文件時，舊內容除非錯誤、過期、重複到造成誤解，或與目前程式碼/路由/欄位/測試結果衝突，否則應保留版本演進脈絡；若確實刪除舊內容，需交代原因。

此變更只修改文件規範，未修改程式碼，因此未重新執行完整 `pytest`、`compileall` 或 Docker 驗證。

實際驗證結果：

```text
rg -n "舊內容|版本如何演進|若確實需要刪除舊內容" AGENTS.md -> found required guidance
git diff --check -> passed
```

## Manual Test 文件新增

日期：2026-05-21

本次新增 `DOCS/manual_test.md`，把 V0.5 Dashboard 手動測試流程整理成可照著操作的繁體中文文件。內容涵蓋 Docker 啟動、`/demo` 開啟、Identity/RBAC、`Try operator create` forbidden case、Normal planner task、approval、Planner/SkillHub、artifact query、fallback planner、blocked domain，以及最小合格檢查清單。

此變更只新增手動測試文件，未修改程式碼，因此未重新執行完整 `pytest`、`compileall` 或 Docker 驗證。

實際驗證結果：

```text
Test-Path DOCS/manual_test.md -> True
rg -n "Browser Agent v0.5 Dashboard|Identity / RBAC|Try operator create|pending_approval|Approve selected|Artifact Query" DOCS/manual_test.md -> found required guidance
git diff --check -> passed
```

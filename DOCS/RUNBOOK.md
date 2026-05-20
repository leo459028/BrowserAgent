# Runbook

本 runbook 涵蓋本機 Docker Compose 的 v0.3 Dashboard 與 artifact governance flow 驗證。Production 仍需要正式 auth/RBAC、secret management、object storage backend、retry/DLQ hardening、以及更強的 browser sandbox isolation。

## 1. 啟動 Stack

```powershell
copy .env.example .env
docker compose up -d --build
```

`api` 與 `worker` services 會在 startup 時執行 `python scripts/bootstrap.py`。Bootstrap 會建立 schema、seed demo identity，並建立 local Kafka topics。

檢查 service status：

```powershell
docker compose ps
```

檢查 API：

```powershell
curl.exe http://localhost:8000/healthz
curl.exe http://localhost:8000/readyz
curl.exe http://localhost:8000/metrics
```

## 2. 開啟 v0.3 Dashboard

```text
http://localhost:8000/demo
```

Dashboard scenarios：

- Normal artifact task：預期 `pending_approval`，approval 後進入 `queued`，接著 worker 寫入 screenshot/html artifacts。
- Redaction metadata task：預期 artifacts 具備 redaction metadata。
- High-risk task：預期 `pending_approval`，並有 high-risk policy reason。
- Sensitive instruction task：預期 `pending_approval`，並有 sensitive-action policy reason。
- Blocked-domain task：預期 `blocked`。

Dashboard observations：

- recent tasks；
- status flow；
- metrics；
- audit timeline；
- steps；
- evaluation；
- screenshot 與 HTML artifacts；
- artifact table：type、content type、size、SHA、backend、redaction status、created time、action；
- Artifact Query panel：metadata JSON 與 access check button。

## 3. 執行 Tests

Host：

```powershell
pytest -q
```

Docker：

```powershell
docker compose exec -T api pytest -q
```

目前預期結果：`24 passed`。

## 4. API Smoke Test

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

curl.exe -X POST http://localhost:8000/v1/tasks `
  -H "Content-Type: application/json" `
  -d $body
```

Approve：

```powershell
curl.exe -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve `
  -H "Content-Type: application/json" `
  -d "{\"approved_by\":\"ops@example.com\",\"note\":\"local v0.3 test\"}"
```

讀取 task：

```powershell
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

讀取 audit：

```powershell
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>/audit
```

開啟 artifact content：

```powershell
curl.exe http://localhost:8000/v1/artifacts/<ARTIFACT_ID>/content
```

成功 task 預期：

- final status 是 `completed`；
- 兩個 artifacts：`screenshot` 與 `html`；
- artifact metadata 具備 `content_type`、`size_bytes`、`backend=local`、`redaction.status=not_applied`；
- artifact content endpoints 回傳 `200`。

## 5. Kafka Topics

列出 topics：

```powershell
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
```

本機預期 topics：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

## 6. Troubleshooting

### `/readyz` 失敗

檢查：

```powershell
docker compose ps
docker compose logs postgres
docker compose exec postgres pg_isready -U agent -d agent
```

### `POST /v1/tasks` 出現 foreign key errors

執行 bootstrap：

```powershell
docker compose exec api python scripts/bootstrap.py
```

### Task 沒有進展

檢查 approval、Kafka、worker：

```powershell
docker compose logs worker
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

### Artifact content 回傳 `403 outside artifact storage`

請確認你呼叫的是寫入 artifact 的同一個 API process。如果 local uvicorn 和 Docker 都使用 port `8000`，測試 Docker 前請先停止 local process。

### Worker Playwright failure

重新 build image：

```powershell
docker compose build --no-cache api worker
```

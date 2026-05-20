# Runbook

本 runbook 用於本機 Docker Compose 與 v0.2 Dashboard 驗證。Production 仍需補
auth、secret management、object store、retry/DLQ、sandbox isolation 與部署
manifest。

## 1. 啟動本機 stack

```powershell
copy .env.example .env
docker compose up --build
```

Compose 會在 `api` 與 `worker` 啟動前執行 `python scripts/bootstrap.py`，建立
schema、seed demo tenant/user，並建立本機 Kafka topics。

檢查：

```powershell
curl.exe http://localhost:8000/healthz
curl.exe http://localhost:8000/readyz
curl.exe http://localhost:8000/metrics
```

## 2. 開啟 v0.2 Dashboard

瀏覽器開啟：

```text
http://localhost:8000/demo
```

Dashboard 可測試四種情境：

- Allowlisted low-risk task：預期進入 `pending_approval`，核准後進入 `queued`。
- High-risk task：預期進入 `pending_approval`，policy reason 顯示 high-risk。
- Sensitive instruction task：預期進入 `pending_approval`，policy reason 顯示 sensitive action。
- Blocked-domain task：預期進入 `blocked`，不能核准。

Dashboard 可觀察：

- 最近 tasks。
- status flow。
- metrics。
- audit timeline。
- steps。
- evaluation。
- screenshot 與 HTML artifact。

## 3. 手動 API 測試

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

curl.exe -X POST http://localhost:8000/v1/tasks -H "Content-Type: application/json" -d $body
```

建立 high-risk task，預期狀態為 `pending_approval`：

```powershell
$body = @{
  title = "Review high-risk task"
  instructions = "Open the allowlisted site and prepare a report."
  priority = 5
  risk_level = "high"
  metadata = @{
    domains = @("example.com")
    start_url = "https://example.com"
    expected_domain = "example.com"
  }
} | ConvertTo-Json -Depth 5

curl.exe -X POST http://localhost:8000/v1/tasks -H "Content-Type: application/json" -d $body
```

核准 task：

```powershell
curl.exe -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve `
  -H "Content-Type: application/json" `
  -d "{\"approved_by\":\"ops@example.com\",\"note\":\"local test\"}"
```

讀取 task：

```powershell
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

讀取 task audit timeline：

```powershell
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>/audit
```

列出最近 tasks：

```powershell
curl.exe http://localhost:8000/v1/tasks?limit=20
```

## 4. Kafka topics

若需要手動建立 topics：

```powershell
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.created --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.queued --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.failed --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.completed --partitions 3 --replication-factor 1
```

## 5. 常見問題

### `/readyz` 失敗

可能原因：

- Postgres 尚未 ready。
- `DATABASE_URL` hostname 不正確。
- DB 尚未建立。

檢查：

```powershell
docker compose ps
docker compose logs postgres
docker compose exec postgres pg_isready -U agent -d agent
```

### `POST /v1/tasks` 發生 foreign key error

可能原因是 demo tenant/user 尚未 seed。執行：

```powershell
docker compose exec api python scripts/bootstrap.py
```

### task 建立後 worker 沒有執行

可能原因：

- task 尚未 approval。
- task 狀態是 `blocked`。
- Kafka topics 尚未建立。
- worker 連不到 Kafka。

檢查：

```powershell
docker compose logs worker
docker compose exec kafka kafka-topics --bootstrap-server kafka:9092 --list
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

### worker Playwright 失敗

可能原因是 Docker image 沒有正確安裝 Chromium browser binary。可重建：

```powershell
docker compose build --no-cache api worker
```

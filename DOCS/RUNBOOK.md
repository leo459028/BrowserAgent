# Runbook

本 runbook 針對本機 Docker Compose 與開發環境。production 仍需補齊 auth、secret management、object store、retry/DLQ、sandbox isolation 與部署 manifest。

## 1. 啟動本機 stack

```powershell
copy .env.example .env
docker compose up --build
```

另開 terminal 檢查：

```powershell
curl.exe http://localhost:8000/healthz
curl.exe http://localhost:8000/readyz
curl.exe http://localhost:8000/metrics
```

## 2. 初始化資料庫

若容器啟動後尚未建表：

```powershell
docker compose exec api alembic upgrade head
```

若 alembic 不可用，可用 bootstrap：

```powershell
docker compose exec api python scripts/bootstrap.py
```

接著 seed API 目前依賴的固定 tenant/user：

```powershell
docker compose exec postgres psql -U agent -d agent -c "INSERT INTO tenants (id, name, status) VALUES ('00000000-0000-0000-0000-000000000001', 'default', 'active') ON CONFLICT (id) DO NOTHING;"
docker compose exec postgres psql -U agent -d agent -c "INSERT INTO users (id, tenant_id, email, role) VALUES ('00000000-0000-0000-0000-000000000002', '00000000-0000-0000-0000-000000000001', 'ops@example.com', 'admin') ON CONFLICT (tenant_id, email) DO NOTHING;"
```

## 3. 建立 Kafka topics

建議用 compose exec，避免 `scripts/create_topics.sh` 預設 container 名稱和實際名稱不同：

```powershell
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.created --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.approved --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.failed --partitions 3 --replication-factor 1
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --create --if-not-exists --topic agent.tasks.completed --partitions 3 --replication-factor 1
```

## 4. 驗證 task flow

建立任務：

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

核准任務：

```powershell
curl.exe -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve `
  -H "Content-Type: application/json" `
  -d "{\"approved_by\":\"00000000-0000-0000-0000-000000000002\",\"note\":\"local test\"}"
```

讀取任務：

```powershell
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

注意：如果仍沿用 README 中的 `approved_by:"ops@example.com"`，可能因 `tasks.approved_by` 是 UUID 欄位而失敗。

## 5. 常見故障與處理

### `/readyz` 失敗

可能原因：

- Postgres 尚未 ready。
- `DATABASE_URL` hostname 不對。
- DB 尚未建立。

處理：

```powershell
docker compose ps
docker compose logs postgres
docker compose exec postgres pg_isready -U agent -d agent
```

### `POST /v1/tasks` 回 500 或 foreign key error

可能原因：固定 tenant/user 未 seed。

處理：執行本文件「初始化資料庫」的 seed SQL。

### 任務建立成功但 worker 不執行

可能原因：

- task 還是 `created` 且未 approval。
- Kafka topics 不存在。
- worker 無法連 Kafka。
- worker 收到 `created` event 但未核准，因此跳過。

處理：

```powershell
docker compose logs worker
docker compose exec kafka kafka-topics.sh --bootstrap-server kafka:9092 --list
curl.exe http://localhost:8000/v1/tasks/<TASK_ID>
```

### worker Playwright 失敗

可能原因：Docker image 沒有安裝 Chromium browser binary。

處理：

```powershell
docker compose exec worker playwright install chromium
```

長期修正：在 `Dockerfile` 補上 `RUN playwright install chromium`。

### domain 被阻擋

可能原因：

- `metadata.domains` 包含不在 `ALLOWLIST_DOMAINS` 的 domain。
- `start_url` 的 host 不在 allowlist。

處理：

- 修改 `.env` 或 compose environment 的 `ALLOWLIST_DOMAINS`。
- 確認 domain 不含 protocol，例如 `example.com`。

### high/critical risk 被 blocked

目前 `risk_level=high|critical` 一律被 `evaluate_task_policy` 擋下，即使 approval API 存在也不會自動解 blocked task。需要修改 policy flow，讓高風險任務進入 `requires_approval` 而不是永久 blocked。

## 6. 停止與清理

停止服務：

```powershell
docker compose down
```

清除資料 volume：

```powershell
docker compose down -v
```

執行 `down -v` 會刪除 PostgreSQL、MinIO 與 artifact volume。

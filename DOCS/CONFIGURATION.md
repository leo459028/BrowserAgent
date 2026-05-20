# Configuration

設定由 `src/browser_agent/config.py` 的 `Settings` 讀取，支援 `.env` 與環境變數。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI title |
| `APP_ENV` | `local` | 執行環境標籤 |
| `APP_LOG_LEVEL` | `INFO` | root logger level |
| `APP_SECRET_KEY` | `change-me` | 未來 auth 用 secret，目前未接正式 auth |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy DB URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL，目前尚未接核心流程 |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka producer/consumer bootstrap servers |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | local artifact 寫入根目錄 |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | policy 與 browser navigation allowlist |
| `MAX_TASK_RETRIES` | `2` | Settings 已定義；worker 目前仍 hardcode retry minimal implementation |
| `TASK_TIMEOUT_SECONDS` | `120` | Settings 已定義；目前尚未傳入 `BrowserRunner` |
| `BROWSER_HEADLESS` | `true` | Playwright 是否 headless |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO endpoint，目前 artifact backend 尚未使用 |
| `MINIO_ACCESS_KEY` | `minio` | MinIO access key |
| `MINIO_SECRET_KEY` | `minio12345` | MinIO secret key |
| `MINIO_BUCKET` | `browser-agent` | MinIO bucket |

`.env.example` 另有 `ARTIFACT_PUBLIC_BASE_URL`，但目前 `Settings` 尚未定義，也未被程式使用。

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 v0.2 Dashboard |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | system of record |
| `redis` | 6379 | 預留 locks/cache/state |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Kafka Topics

`scripts/bootstrap.py` 與 compose bootstrap 會建立：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

目前程式實際發布：

- `agent.tasks.created`
- `agent.tasks.queued`

目前 worker 實際消費：

- `agent.tasks.queued`

Roadmap 中提到但尚未落地：

- `agent.tasks.planned`
- `agent.tasks.executing`
- `agent.tasks.progress`
- `agent.tasks.artifacts`
- `agent.tasks.dlq`

## Playwright

`Dockerfile` 會安裝 Chromium：

```dockerfile
RUN playwright install --with-deps chromium
```

`docker compose up --build` 第一次會下載 Chromium/headless shell/FFmpeg，時間較久。

## Artifacts

目前 artifact 寫入 local filesystem 的 `ARTIFACT_BASE_PATH`，並同步新增
`task_artifacts` row。路徑格式：

```text
<base>/<YYYY>/<MM>/<DD>/<task_id>/<artifact_type>-<sha12>.<suffix>
```

目前即使 compose 啟動了 MinIO，也尚未呼叫 boto3 或 MinIO API。v0.3 建議改成：

- 抽象 artifact backend。
- 保留 local backend，新增 MinIO/S3 backend。
- 將 object URI、checksum、content type、size、retention metadata 寫入 `task_artifacts`。
- 增加 tenant/task scoped access control。


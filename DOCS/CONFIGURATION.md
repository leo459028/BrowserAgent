# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_ENV` | `local` | Environment label |
| `APP_LOG_LEVEL` | `INFO` | Root logger level |
| `APP_SECRET_KEY` | `change-me` | 預留給 auth/session；目前尚未使用 |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL；目前尚未用於 locks/dedupe/rate limiting |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka producer/consumer bootstrap servers |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | Local artifact root path |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | Policy 與 browser navigation allowlist |
| `MAX_TASK_RETRIES` | `2` | Settings 欄位；目前 worker consumer helper 預設 3 次，尚未接入此設定 |
| `TASK_TIMEOUT_SECONDS` | `120` | Settings 欄位；目前 `BrowserRunner` constructor 預設 120 秒 |
| `BROWSER_HEADLESS` | `true` | Playwright headless mode |
| `MINIO_ENDPOINT` | `minio:9000` | 預留給 S3/MinIO artifact backend |
| `MINIO_ACCESS_KEY` | `minio` | 預留值 |
| `MINIO_SECRET_KEY` | `minio12345` | 預留值 |
| `MINIO_BUCKET` | `browser-agent` | 預留值 |

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 v0.4 Dashboard |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | 預留 locks/cache/state service |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | Task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Kafka Topics

當 `BOOTSTRAP_KAFKA_TOPICS=true` 時，`scripts/bootstrap.py` 會建立：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

目前事件流：

- API publish `agent.tasks.created`。
- Approval 後 API publish `agent.tasks.queued`。
- Worker consume `agent.tasks.queued`。

## Playwright

Docker image 會安裝 Chromium：

```dockerfile
RUN playwright install --with-deps chromium
```

Browser actions 由 `src/browser_agent/services/browser.py` 執行，支援：

- `goto`
- `click`
- `fill`
- `press`
- `wait`
- `extract_text`
- `screenshot`

## Artifacts

Active artifact backend 是 `ARTIFACT_BASE_PATH` 底下的 local filesystem storage。

Path format：

```text
<base>/<YYYY>/<MM>/<DD>/<task_id>/<artifact_type>-<sha12>.<suffix>
```

寫入 `task_artifacts.metadata` 的 artifact metadata 包含：

- `backend`，目前為 `local`。
- `content_type`。
- `media_type`，content type compatibility alias。
- `size_bytes`。
- `retention`，default policy metadata。
- `redaction`，default no-op hook metadata。

MinIO 目前存在於 Docker Compose，但程式尚未把 artifacts upload 到 MinIO。

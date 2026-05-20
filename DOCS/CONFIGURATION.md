# Configuration

設定由 `src/browser_agent/config.py` 透過 Pydantic settings 載入。Environment values 可由 `.env` 或 Docker Compose 提供。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_ENV` | `local` | Environment label |
| `APP_LOG_LEVEL` | `INFO` | root logger level |
| `APP_SECRET_KEY` | `change-me` | 預留給未來 auth/session |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL，目前預留 |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka producer/consumer bootstrap servers |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | local artifact root path |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | policy/browser navigation allowlist |
| `MAX_TASK_RETRIES` | `2` | 設定值；worker retry 目前是 minimal implementation |
| `TASK_TIMEOUT_SECONDS` | `120` | 設定值；browser runner 目前有 minimal timeout support |
| `BROWSER_HEADLESS` | `true` | Playwright headless mode |
| `MINIO_ENDPOINT` | `minio:9000` | 預留給未來 S3/MinIO artifact backend |
| `MINIO_ACCESS_KEY` | `minio` | 預留 |
| `MINIO_SECRET_KEY` | `minio12345` | 預留 |
| `MINIO_BUCKET` | `browser-agent` | 預留 |

## Docker Compose Services

| Service | Port | 用途 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 v0.3 Dashboard |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | system of record |
| `redis` | 6379 | 預留 locks/cache/state service |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Kafka Topics

當 `BOOTSTRAP_KAFKA_TOPICS=true` 時，`scripts/bootstrap.py` 會建立本機 topics：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

目前使用情況：

- API publish `agent.tasks.created` 與 `agent.tasks.queued`。
- Worker consume `agent.tasks.queued`。

## Playwright

Docker image 會安裝 Chromium：

```dockerfile
RUN playwright install --with-deps chromium
```

## Artifacts

目前 v0.3 active artifact backend 是 `ARTIFACT_BASE_PATH` 底下的 local filesystem storage。

Path format：

```text
<base>/<YYYY>/<MM>/<DD>/<task_id>/<artifact_type>-<sha12>.<suffix>
```

寫入 `task_artifacts.metadata` 的 artifact metadata 包含：

- `backend`：目前為 `local`；
- `content_type`；
- `size_bytes`；
- `retention`：default policy metadata；
- `redaction`：default no-op hook metadata；
- `media_type`：content type 的 compatibility alias。

MinIO 目前存在於 Docker Compose，但程式尚未把 artifacts upload 到 MinIO。

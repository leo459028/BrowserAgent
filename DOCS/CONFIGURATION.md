# 設定文件

設定由 `src/browser_agent/config.py` 的 `Settings` 類別管理，會讀取 `.env`。範例設定在 `.env.example`。

## 環境變數

| 變數 | 預設/範例 | 用途 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI title |
| `APP_ENV` | `local` | 執行環境標記 |
| `APP_LOG_LEVEL` | `INFO` | root logger level |
| `APP_SECRET_KEY` | `change-me` | 預留 secret，目前未使用於 auth |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy DB 連線 |
| `REDIS_URL` | `redis://redis:6379/0` | Redis 連線，程式目前未使用 |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka producer/consumer |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | 本地 artifact 寫入根目錄 |
| `ARTIFACT_PUBLIC_BASE_URL` | `http://localhost:9000` | 範例中存在，但 Settings 尚未定義 |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO endpoint，目前 artifact store 未使用 |
| `MINIO_ACCESS_KEY` | `minio` | MinIO access key |
| `MINIO_SECRET_KEY` | `minio12345` | MinIO secret key |
| `MINIO_BUCKET` | `browser-agent` | MinIO bucket |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | Policy 與 browser navigation allowlist |
| `MAX_TASK_RETRIES` | `2` | Settings 有定義，worker 尚未使用 |
| `TASK_TIMEOUT_SECONDS` | `120` | Settings 有定義，但 `TaskRunner` 沒有傳給 `BrowserRunner` |
| `BROWSER_HEADLESS` | `true` | Playwright 是否 headless |

## Docker Compose 服務

| Service | Port | 用途 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | system of record |
| `redis` | 6379 | 預留 locks/cache/state |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Kafka topics

程式目前會發布/消費：

- `agent.tasks.created`
- `agent.tasks.approved`

`scripts/create_topics.sh` 另外建立：

- `agent.tasks.failed`
- `agent.tasks.completed`

藍圖提到但目前尚未落地的 topics：

- `agent.tasks.planned`
- `agent.tasks.executing`
- `agent.tasks.progress`
- `agent.tasks.artifacts`
- `agent.tasks.dlq`

## Playwright 設定注意

`Dockerfile` 會執行：

```dockerfile
RUN playwright install --with-deps chromium
```

第一次 `docker compose up --build` 會下載 Chromium、headless shell、FFmpeg 與必要 Linux runtime，時間會較久。後續 build 通常會吃 Docker layer cache。

## Artifact 設定注意

目前 artifact 寫到 `ARTIFACT_BASE_PATH`，並同步寫入 `task_artifacts` 資料表。路徑格式：

```text
<base>/<YYYY>/<MM>/<DD>/<task_id>/<artifact_type>-<sha12>.<suffix>
```

即使 compose 啟動了 MinIO，v0.1 現在仍未呼叫 boto3 或 MinIO API。若要 production 化，應改成：

- 本地暫存檔
- 上傳 object store
- 將 object URI、checksum、content type 與 retention metadata 寫入 `task_artifacts`
- 依 tenant/task 設定 retention policy

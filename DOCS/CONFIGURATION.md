# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_VERSION` | `1.0.0` | App/API version |
| `APP_ENV` | `local` | Environment label |
| `APP_SECRET_KEY` | `change-me` | local token HS256 secret；正式環境不可使用預設值 |
| `AUTH_ENABLED` | `true` | 是否啟用 Bearer token 驗證 |
| `AUTH_MODE` | `local` | `local` 或 `jwks` |
| `AUTH_JWKS_URL` | `https://idp.example/jwks.json` | JWKS verifier URL |
| `AUTH_LOCAL_TOKENS_ENABLED` | `true` | 是否啟用 `/v1/auth/local-token` |
| `AUTH_JWT_ISSUER` | `browser-agent-local` | JWT `iss` |
| `AUTH_JWT_AUDIENCE` | `browser-agent-api` | JWT `aud` |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL |
| `RELIABILITY_STORE` | `redis` | `memory` 或 `redis` |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka bootstrap servers |
| `ARTIFACT_BACKEND` | `s3` | `local` 或 `s3` |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | Local artifact root path |
| `MINIO_ENDPOINT` | `minio:9000` | MinIO/S3-compatible endpoint |
| `MINIO_ACCESS_KEY` | `minio` | S3 access key |
| `MINIO_SECRET_KEY` | `minio12345` | S3 secret key |
| `MINIO_BUCKET` | `browser-agent` | Artifact bucket |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | Browser allowlist |
| `TASK_CREATE_RATE_LIMIT_PER_MINUTE` | `60` | Task create rate limit |
| `TASK_LOCK_TTL_SECONDS` | `300` | Worker task lock TTL |
| `MAX_TASK_RETRIES` | `2` | Worker final failure 前最大嘗試次數 |
| `WORKER_SERVICE_ID` | `worker-local` | Worker audit actor identity |
| `DLQ_TOPIC` | `agent.tasks.dlq` | DLQ topic |

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 Operations Center |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | Reliability store |
| `kafka` | 9092 | Task event bus |
| `minio` | 9000, 9001 | Active S3-compatible artifact backend |

Docker Compose 預設 `ARTIFACT_BACKEND=s3`，`scripts/bootstrap.py` 會確認 bucket 已建立。

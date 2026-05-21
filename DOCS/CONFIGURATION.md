# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_ENV` | `local` | Environment label |
| `APP_LOG_LEVEL` | `INFO` | Root logger level |
| `APP_SECRET_KEY` | `change-me` | v0.5 local JWT HS256 secret；正式環境不可使用預設值 |
| `AUTH_ENABLED` | `true` | 是否啟用 Bearer token 驗證 |
| `AUTH_JWT_ISSUER` | `browser-agent-local` | JWT `iss` |
| `AUTH_JWT_AUDIENCE` | `browser-agent-api` | JWT `aud` |
| `AUTH_TOKEN_TTL_SECONDS` | `3600` | demo token TTL |
| `AUTH_DEMO_TOKENS_ENABLED` | `true` | 是否啟用 `/v1/auth/demo-token` |
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
| `api` | 8000 | FastAPI control plane 與 v0.5 Dashboard |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | 預留 locks/cache/state service |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | Task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Auth/RBAC

v0.5 使用本機 JWT 作為 OIDC-compatible scaffold。正式部署時應改成真實 OIDC/JWKS verifier，並關閉 `AUTH_DEMO_TOKENS_ENABLED`。

Role 與主要權限：

- `creator`：task create/read、artifact read。
- `approver`：task read/audit/approve、artifact read。
- `operator`：task read/audit、artifact read、metrics read。
- `admin`：全部權限，包含 SkillHub registration。

## Kafka Topics

當 `BOOTSTRAP_KAFKA_TOPICS=true` 時，`scripts/bootstrap.py` 會建立：

- `agent.tasks.created`
- `agent.tasks.queued`
- `agent.tasks.failed`
- `agent.tasks.completed`

## Artifacts

Active artifact backend 是 `ARTIFACT_BASE_PATH` 底下的 local filesystem storage。MinIO 目前存在於 Docker Compose，但程式尚未把 artifacts upload 到 MinIO。

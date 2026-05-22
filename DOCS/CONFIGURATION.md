# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_ENV` | `local` | Environment label |
| `APP_LOG_LEVEL` | `INFO` | Root logger level |
| `APP_SECRET_KEY` | `change-me` | local JWT HS256 secret；正式環境不可使用預設值 |
| `AUTH_ENABLED` | `true` | 是否啟用 Bearer token 驗證 |
| `AUTH_JWT_ISSUER` | `browser-agent-local` | JWT `iss` |
| `AUTH_JWT_AUDIENCE` | `browser-agent-api` | JWT `aud` |
| `AUTH_TOKEN_TTL_SECONDS` | `3600` | demo token TTL |
| `AUTH_DEMO_TOKENS_ENABLED` | `true` | 是否啟用 `/v1/auth/demo-token` |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | SQLAlchemy database URL |
| `REDIS_URL` | `redis://redis:6379/0` | Redis URL；Docker reliability store 使用 |
| `RELIABILITY_STORE` | `redis` | `memory` 或 `redis`；host 預設 `memory`，Docker 預設 `redis` |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka producer/consumer bootstrap servers |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | Local artifact root path |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | Policy 與 browser navigation allowlist |
| `TASK_CREATE_RATE_LIMIT_PER_MINUTE` | `60` | 每個 tenant/user 每分鐘 task create 上限；超過回 `429` |
| `IDEMPOTENCY_TTL_SECONDS` | `86400` | idempotency policy 設定；目前 DB task record 為主要去重來源 |
| `TASK_LOCK_TTL_SECONDS` | `300` | worker task lock TTL |
| `MAX_TASK_RETRIES` | `2` | worker final failure 前最大嘗試次數 |
| `TASK_TIMEOUT_SECONDS` | `120` | Playwright action timeout seconds |
| `BROWSER_HEADLESS` | `true` | Playwright headless mode |
| `WORKER_SERVICE_ID` | `worker-local` | worker audit actor 會顯示為 `service:<WORKER_SERVICE_ID>` |
| `DLQ_TOPIC` | `agent.tasks.dlq` | worker final failure 發布的 DLQ topic |
| `MINIO_ENDPOINT` | `minio:9000` | 預留給 S3/MinIO artifact backend |
| `MINIO_ACCESS_KEY` | `minio` | 預留值 |
| `MINIO_SECRET_KEY` | `minio12345` | 預留值 |
| `MINIO_BUCKET` | `browser-agent` | 預留值 |

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 v0.6 Dashboard |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | v0.6 reliability store：rate limit 與 task locks |
| `zookeeper` | 2181 | Kafka dependency |
| `kafka` | 9092 | Task event bus |
| `minio` | 9000, 9001 | 預留 artifact object store |

## Auth/RBAC

v0.6 仍使用本機 JWT 作為 OIDC-compatible scaffold。正式部署時應改成真實 OIDC/JWKS verifier，並關閉 `AUTH_DEMO_TOKENS_ENABLED`。

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
- `agent.tasks.dlq`

## Reliability

Docker Compose 設定 `RELIABILITY_STORE=redis`，API 會用 Redis 做 task create rate limiting，worker 會用 Redis lock 避免同一 task 重複執行。未設定 `.env` 的 host/unit test 預設 `memory`，不需要外部 Redis。

`Idempotency-Key` 的主要去重來源是 database 中的 `tasks.idempotency_key` 與 `tasks.metadata.reliability.request_hash`。`IDEMPOTENCY_TTL_SECONDS` 是目前 policy/config 設定，尚未做背景清理過期 task。

## Artifacts

Active artifact backend 是 `ARTIFACT_BASE_PATH` 底下的 local filesystem storage。MinIO 目前存在於 Docker Compose，但程式尚未把 artifacts upload 到 MinIO。

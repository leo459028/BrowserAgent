# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_VERSION` | `1.2.0` | App/API version |
| `APP_ENV` | `local` | Environment label |
| `APP_SECRET_KEY` | `change-me` | local token HS256 secret；正式環境不可使用預設值 |
| `AUTH_ENABLED` | `true` | 是否啟用 Bearer token 驗證 |
| `AUTH_MODE` | `local` | `local` 或 `jwks` |
| `AUTH_JWKS_URL` | `https://idp.example/jwks.json` | JWKS verifier URL |
| `AUTH_OIDC_ISSUER_URL` | `https://idp.example` | OIDC issuer URL；未設定 `AUTH_JWKS_URL` 時用 discovery 取得 `jwks_uri` |
| `AUTH_JWKS_CACHE_TTL_SECONDS` | `300` | JWKS/OIDC JSON 快取秒數 |
| `AUTH_JWKS_REQUEST_TIMEOUT_SECONDS` | `5` | JWKS/OIDC HTTP timeout 秒數 |
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
| `WORKER_RECORD_VIDEO_DEFAULT` | `false` | Worker 是否預設對所有任務錄製全行程 WebM 視訊 |
| `SCHEDULER_ENABLED` | `true` | 是否啟用 Scheduled Tasks 定時巡檢調度引擎 |
| `DLQ_TOPIC` | `agent.tasks.dlq` | DLQ topic |
| `ALERT_WEBHOOK_URL` | `https://hooks.slack.com/services/...` | 外部告警 Webhook 接收端點（支援 Slack / Discord 相容 JSON） |
| `ALERT_WEBHOOK_TIMEOUT_SECONDS` | `3.0` | 外部 Webhook 呼叫超時上限（秒） |
| `ALERT_EVALUATION_INTERVAL_SECONDS` | `60` | 告警中心自動評估週期（秒） |
| `ALERT_FAILURE_RATE_THRESHOLD` | `0.3` | 觸發 Warning 告警之任務失敗率閾值（預設 30%） |
| `ALERT_DLQ_THRESHOLD` | `5` | 觸發 Warning 告警之 DLQ 失敗任務積壓數量閾值 |
| `ALERT_PENDING_APPROVAL_THRESHOLD` | `10` | 觸發 Info 告警之待人工審核任務數量閾值 |
| `OTEL_ENABLED` | `false` | 是否啟用 OTLP Exporter 即時串流推送 |
| `OTEL_SERVICE_NAME` | `browser-agent` | OTEL service name 與 log correlation service 名稱 |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318/v1/traces` | OTLP HTTP/JSON 收集端點 |
| `OTEL_RESOURCE_ATTRIBUTES` | `service.namespace=browser-agent` | OTLP Resource attributes 鍵值對 |
| `OTEL_PROPAGATORS` | `tracecontext,baggage` | W3C TraceContext 格式傳播宣告 |

## Kubernetes Deployment (`deploy/k8s/`)

V1.2 提供生產級 Kubernetes Kustomization 套件：

```text
deploy/k8s/
├── kustomization.yaml
├── configmap.yaml
├── secret.example.yaml
├── service.yaml
├── api-deployment.yaml
├── worker-deployment.yaml
├── ingress.yaml
└── keda-worker-scaledobject.yaml
```

檢驗語法：
```powershell
kubectl kustomize deploy/k8s/
```

套用部署（需預先建立 `browser-agent-secret`）：
```powershell
kubectl apply -k deploy/k8s/
```

KEDA 自動擴展：
`keda-worker-scaledobject.yaml` 監控 Kafka `agent.tasks.queued` 之 consumer group lag，當積壓任務增加時自動將 Worker Pod 由 1 擴展至 10。

## V1.2 Production-like Compose

V1.2 提供 `.env.production.example` 與 `docker-compose.prod.yml`，可用來審查 production-like Compose 設定：

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

這份範本預設：

- `APP_ENV=production`
- `APP_VERSION=1.2.0`
- `AUTH_MODE=jwks`
- `AUTH_LOCAL_TOKENS_ENABLED=false`
- `RELIABILITY_STORE=redis`
- `ARTIFACT_BACKEND=s3`
- `SCHEDULER_ENABLED=true`
- `OTEL_ENABLED=false`

它是 Compose production readiness baseline；企業生產上線建議搭配 `deploy/k8s/` 進行 Kubernetes 部署。

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 Operations Center |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | Reliability store 與排程分散式搶鎖 |
| `kafka` | 9092 | Task event bus |
| `minio` | 9000, 9001 | Active S3-compatible artifact backend |

Docker Compose 預設 `ARTIFACT_BACKEND=s3`，`scripts/bootstrap.py` 會確認 bucket 已建立。

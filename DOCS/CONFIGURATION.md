# Configuration

設定由 [src/browser_agent/config.py](../src/browser_agent/config.py) 的 Pydantic settings 讀取，可來自 `.env` 或 Docker Compose environment。

## Environment Variables

| Variable | Example | 說明 |
|---|---|---|
| `APP_NAME` | `browser-agent` | FastAPI app title |
| `APP_VERSION` | `1.3.0` | App/API version |
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
| `AUTH_OIDC_CLIENT_ID` | `browser-agent-client` | OIDC SSO 授權 Client ID |
| `AUTH_OIDC_CLIENT_SECRET` | `secret` | OIDC SSO 授權 Client Secret |
| `AUTH_OIDC_REDIRECT_URI` | `http://localhost:8000/v1/auth/oidc/callback` | OIDC SSO Callback 回調 URL |
| `AUTH_OIDC_SCOPES` | `openid profile email` | OIDC 请求之授權範圍 Scopes |
| `AUTH_COOKIE_NAME` | `ba_session` | 登入會話 HttpOnly Cookie 名稱 |
| `KMS_PROVIDER` | `local` | KMS 驅動提供者：`local`、`aws_kms`、`vault` |
| `KMS_KEY_ID` | `session-vault-v1` | KMS 主加密金鑰 Identifier |
| `KMS_SECRET_KEY` | `local-kms-master-key-32-chars!` | Local KMS 主金鑰字串（至少 32 字元） |
| `KMS_REGION` | `us-east-1` | AWS KMS 區域 |
| `KMS_VAULT_ADDR` | `http://vault:8200` | HashiCorp Vault 伺服器位址 |
| `KMS_VAULT_TOKEN` | `vault-token` | HashiCorp Vault 存取 Token |
| `KAFKA_TOPIC_HIGH` | `agent.tasks.high` | 高優先權任務主題（priority > 0） |
| `KAFKA_TOPIC_QUEUED` | `agent.tasks.queued` | 標準常規任務主題（priority == 0） |
| `KAFKA_TOPIC_BATCH` | `agent.tasks.batch` | 批次低優先權主題（priority < 0） |
| `WORKER_POOL_NAME` | `default` | Worker 資源池識別名稱（如 `high-priority`, `batch-pool`） |
| `TELEMETRY_STREAM_ENABLED` | `true` | 是否啟用 WebSocket 即時畫面廣播串流 |
| `TELEMETRY_STREAM_FPS` | `2` | 畫面幀廣播速率（每秒幀數，預設 2 FPS） |
| `SELF_HEALING_ENABLED` | `true` | 是否啟用啟發式多維選擇器自我修復引擎 |
| `SELF_HEALING_SIMILARITY_THRESHOLD` | `0.6` | 自癒標籤相似度匹配門檻（0.0 ~ 1.0） |
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

## Enterprise Helm 3 Chart 套件 (`deploy/helm/browser-agent/`)

V1.3 提供正式 Enterprise Helm 3 Chart 套件與 GitOps ArgoCD 應用清單：

```text
deploy/helm/browser-agent/
├── Chart.yaml                  # Chart 定義（版本 1.3.0）
├── values.yaml                 # 預設生產級變數配置
└── templates/
    ├── NOTES.txt               # 安裝後指引
    ├── _helpers.tpl            # 命名與標籤模板
    ├── configmap.yaml          # 全域環境配置
    ├── secret.yaml             # 機密金鑰與 KMS 憑證
    ├── api-deployment.yaml     # FastAPI Control Plane Pods
    ├── api-service.yaml        # API Service 與端口
    ├── worker-deployment.yaml  # Playwright Worker 資源池 Pods
    ├── ingress.yaml            # Ingress 路由規則
    └── keda-scaledobject.yaml  # Kafka Lag 自動水平擴展宣告
```

Chart 語法與模板渲染檢驗：
```powershell
helm lint deploy/helm/browser-agent
helm template browser-agent deploy/helm/browser-agent
```

GitOps ArgoCD 部署藍圖：
`deploy/gitops/argocd-application.yaml` 提供聲明式持續部署 Application 物件，支援自動同步（`automated.prune` & `automated.selfHeal`）。

## Kubernetes Deployment (`deploy/k8s/`)

保留原生 Kubernetes Kustomization 套件：

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

## V1.3 Production-like Compose

V1.3 提供 `.env.production.example` 與 `docker-compose.prod.yml`，可用來審查 production-like Compose 設定：

```powershell
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

這份範本預設：

- `APP_ENV=production`
- `APP_VERSION=1.3.0`
- `AUTH_MODE=jwks`
- `AUTH_LOCAL_TOKENS_ENABLED=false`
- `RELIABILITY_STORE=redis`
- `ARTIFACT_BACKEND=s3`
- `SCHEDULER_ENABLED=true`
- `OTEL_ENABLED=false`
- `KMS_PROVIDER=local`
- `TELEMETRY_STREAM_ENABLED=true`
- `SELF_HEALING_ENABLED=true`

它是 Compose production readiness baseline；企業生產上線建議搭配 `deploy/helm/browser-agent/` 或 `deploy/k8s/` 進行 Kubernetes 部署。

## Docker Compose Services

| Service | Port | 說明 |
|---|---:|---|
| `api` | 8000 | FastAPI control plane 與 Operations Center |
| `worker` | none | Kafka consumer + Playwright runner |
| `postgres` | 5432 | System of record |
| `redis` | 6379 | Reliability store 與排程分散式搶鎖 |
| `kafka` | 9092 | Task event bus (high, queued, batch, dlq) |
| `minio` | 9000, 9001 | Active S3-compatible artifact backend |

Docker Compose 預設 `ARTIFACT_BACKEND=s3`，`scripts/bootstrap.py` 會確認 bucket 已建立。

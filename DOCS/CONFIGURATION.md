# Configuration Guide

Configuration settings in BrowserAgent are managed through Pydantic BaseSettings in [src/browser_agent/config.py](../src/browser_agent/config.py). Settings can be injected via `.env` files, shell environment variables, or container orchestrators (Docker Compose, Kubernetes ConfigMaps/Secrets).

---

## Environment Variables Reference

| Variable | Default / Example | Description |
| :--- | :--- | :--- |
| `APP_NAME` | `browser-agent` | Application name displayed in OpenAPI documentation and headers. |
| `APP_VERSION` | `1.4.2` | Semantic release version. |
| `APP_ENV` | `local` | Deployment environment identifier (`local`, `staging`, `production`). |
| `APP_LOG_LEVEL` | `INFO` | Logging verbosity (`DEBUG`, `INFO`, `WARNING`, `ERROR`). |
| `APP_SECRET_KEY` | `change-me` | Secret key used to sign local development HS256 tokens. Must be modified in production. |
| `DEFAULT_BROWSER_ENGINE` | `chromium` | Default Playwright execution engine (`chromium`, `firefox`, `webkit`). |
| `DLP_ENABLED` | `true` | Enables Zero-Trust Dynamic Data Loss Prevention (DLP). |
| `DLP_MASK_PASSWORDS` | `true` | Injects dynamic CSS Gaussian blur masks (`filter: blur(8px)`) onto password input elements. |
| `DLP_REDACT_TOKENS` | `true` | Enables regex-based redaction of Bearer tokens, API keys, and sensitive secrets in metadata. |
| `FEDERATION_ENABLED` | `true` | Enables multi-cluster scheduling federation and disaster recovery failover. |
| `FEDERATION_NODE_ID` | `node-local-1` | Unique node identifier in the multi-cluster federation topology. |
| `FEDERATION_REGION` | `local-dev` | Geographic or cloud region identifier for the node (e.g., `us-east-1`). |
| `FEDERATION_HEARTBEAT_INTERVAL_SECONDS` | `10` | Heartbeat interval (seconds) for renewing distributed leader leases. |
| `FEDERATION_LEASE_TTL_SECONDS` | `30` | Expiration TTL (seconds) for scheduler leader leases before triggering re-election. |
| `REMOTE_TAKEOVER_ENABLED` | `true` | Enables bidirectional remote takeover and Human-in-the-Loop (HITL) interactive channel. |
| `REMOTE_TAKEOVER_TIMEOUT_SECONDS` | `300` | Maximum wait timeout (seconds) for an operator during a paused takeover session. |
| `AUTH_ENABLED` | `true` | Enforces authentication and RBAC checks across protected endpoints. |
| `AUTH_MODE` | `local` | Authentication mode: `local` (HS256 tokens) or `jwks` (RS256 IdP verification). |
| `AUTH_JWKS_URL` | `https://idp.example/jwks.json` | JWKS endpoint URL for fetching RS256 public keys. |
| `AUTH_OIDC_ISSUER_URL` | `https://idp.example` | OIDC issuer URL for dynamic discovery when `AUTH_JWKS_URL` is omitted. |
| `AUTH_JWKS_CACHE_TTL_SECONDS` | `300` | In-memory cache duration (seconds) for fetched JWKS keysets. |
| `AUTH_JWKS_REQUEST_TIMEOUT_SECONDS` | `5` | Network timeout (seconds) for fetching JWKS keysets. |
| `AUTH_LOCAL_TOKENS_ENABLED` | `true` | Enables the `/v1/auth/local-token` endpoint (must be `false` in production). |
| `AUTH_JWT_ISSUER` | `browser-agent-local` | Expected JWT issuer (`iss` claim). |
| `AUTH_JWT_AUDIENCE` | `browser-agent-api` | Expected JWT audience (`aud` claim). |
| `AUTH_OIDC_CLIENT_ID` | `browser-agent-client` | Client ID for Enterprise OIDC Authorization Code Flow. |
| `AUTH_OIDC_CLIENT_SECRET` | `secret` | Client Secret for Enterprise OIDC Authorization Code Flow. |
| `AUTH_OIDC_REDIRECT_URI` | `http://localhost:8000/v1/auth/oidc/callback` | Callback redirect URI registered with the identity provider. |
| `KMS_PROVIDER` | `local` | Key Management Service provider driver (`local`, `aws`, `vault`). |
| `KMS_KEY_ID` | `local-kek-v1` | Key identifier for the Key Encryption Key (KEK). |
| `KMS_MASTER_KEY` | `01234567890123456789012345678901` | 32-byte master key for local AES-256-GCM envelope encryption. |
| `KMS_REGION` | `us-east-1` | AWS region when using `KMS_PROVIDER=aws`. |
| `VAULT_ADDR` | `http://localhost:8200` | HashiCorp Vault server address when using `KMS_PROVIDER=vault`. |
| `VAULT_TOKEN` | `vault-token` | HashiCorp Vault authentication token. |
| `MULTI_PRIORITY_ENABLED` | `true` | Enables priority topic partitioning (`agent.tasks.high`, `queued`, `batch`). |
| `QUEUE_HIGH_TOPIC` | `agent.tasks.high` | High-priority task Kafka topic. |
| `QUEUE_DEFAULT_TOPIC` | `agent.tasks.queued` | Standard-priority task Kafka topic. |
| `QUEUE_BATCH_TOPIC` | `agent.tasks.batch` | Low-priority batch task Kafka topic. |
| `WORKER_POOL` | `default` | Worker pool identifier for topic subscription isolation. |
| `LIVE_BROADCAST_ENABLED` | `true` | Enables real-time browser frame streaming via WebSockets. |
| `SELF_HEALING_ENABLED` | `true` | Enables heuristic multi-attribute selector self-healing cascade. |
| `SELF_HEALING_THRESHOLD` | `0.75` | Minimum similarity threshold required to adopt a self-healed selector. |
| `DATABASE_URL` | `postgresql+psycopg://agent:agent@postgres:5432/agent` | PostgreSQL database connection string. |
| `REDIS_URL` | `redis://redis:6379/0` | Redis instance connection string. |
| `RELIABILITY_STORE` | `redis` | Reliability backend store (`redis` or `memory`). |
| `KAFKA_BOOTSTRAP_SERVERS` | `kafka:9092` | Kafka broker bootstrap list. |
| `DLQ_TOPIC` | `agent.tasks.dlq` | Dead Letter Queue topic for permanently failed tasks. |
| `ARTIFACT_BACKEND` | `s3` | Artifact storage driver (`local` or `s3`). |
| `ARTIFACT_BASE_PATH` | `/data/artifacts` | Filesystem root path when using local artifact storage. |
| `MINIO_ENDPOINT` | `minio:9000` | S3-compatible object storage endpoint. |
| `MINIO_ACCESS_KEY` | `minio` | S3 storage access key ID. |
| `MINIO_SECRET_KEY` | `minio12345` | S3 storage secret access key. |
| `MINIO_BUCKET` | `browser-agent` | S3 bucket name for task artifacts and session vaults. |
| `ALLOWLIST_DOMAINS` | `example.com,example.org` | Comma-separated domain boundary allowlist for browser navigation. |
| `TASK_CREATE_RATE_LIMIT_PER_MINUTE` | `60` | Client rate limit per minute for task submissions. |
| `TASK_LOCK_TTL_SECONDS` | `300` | Distributed lock lease duration for executing workers. |
| `MAX_TASK_RETRIES` | `2` | Maximum retry attempts before routing a task to DLQ. |
| `TASK_TIMEOUT_SECONDS` | `120` | Execution timeout per task in seconds. |
| `BROWSER_HEADLESS` | `true` | Launches Playwright in headless mode. |
| `WORKER_SERVICE_ID` | `worker-local` | Worker identity recorded in execution audit logs. |
| `WORKER_RECORD_VIDEO_DEFAULT` | `true` | Automatically records WebM full-session video for every task run. |
| `SCHEDULER_ENABLED` | `true` | Enables background Cron schedule evaluation. |
| `ALERT_WEBHOOK_URL` | `https://hooks.slack.com/...` | Slack/Discord webhook URL for production alert notifications. |
| `ALERT_DLQ_THRESHOLD` | `5` | DLQ backlog threshold triggering Warning alert. |
| `ALERT_AUTH_FAILURES_THRESHOLD` | `10` | Authentication failures threshold triggering Warning alert. |
| `ALERT_QUARANTINE_THRESHOLD` | `3` | Quarantined tasks threshold triggering Warning alert. |
| `ALERT_WEBHOOK_TIMEOUT_SECONDS` | `3.0` | Network timeout for outbound webhook dispatches. |
| `OTEL_ENABLED` | `false` | Enables OpenTelemetry OTLP batch span streaming. |
| `OTEL_SERVICE_NAME` | `browser-agent` | Service name attached to exported spans and traces. |
| `OTEL_EXPORTER_OTLP_ENDPOINT` | `http://otel-collector:4318/v1/traces` | OTLP HTTP/JSON receiver endpoint. |
| `OTEL_RESOURCE_ATTRIBUTES` | `service.namespace=browser-agent` | Standard OpenTelemetry resource attribute key-value pairs. |
| `OTEL_PROPAGATORS` | `tracecontext,baggage` | W3C context propagation headers. |

---

## Enterprise Helm 3 Deployment (`deploy/helm/browser-agent/`)

BrowserAgent provides production-ready Helm 3 chart templates under `deploy/helm/browser-agent/`:

```text
deploy/helm/browser-agent/
├── Chart.yaml                  # Chart definition (version 1.4.2)
├── values.yaml                 # Production default configurations
└── templates/
    ├── NOTES.txt               # Post-installation instructions
    ├── _helpers.tpl            # Template helper macros
    ├── configmap.yaml          # Global environment variables
    ├── secret.yaml             # Encrypted secrets and KMS configurations
    ├── api-deployment.yaml     # FastAPI Control Plane deployment
    ├── api-service.yaml        # Control plane ClusterIP service
    ├── worker-deployment.yaml  # Playwright Worker fleet deployment
    ├── ingress.yaml            # Ingress routing rules
    └── keda-scaledobject.yaml  # KEDA Kafka Lag horizontal autoscaler
```

### Validating Helm Templates:
```bash
helm lint deploy/helm/browser-agent
helm template browser-agent deploy/helm/browser-agent
```

### GitOps ArgoCD Blueprint:
A declarative continuous delivery application manifest is provided at `deploy/gitops/argocd-application.yaml`, supporting automated drift detection, pruning, and self-healing.

---

## Kubernetes Kustomize Manifests (`deploy/k8s/`)

For environments using raw Kubernetes manifests, a complete Kustomize package is available:

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

Inspect rendered manifests:
```bash
kubectl kustomize deploy/k8s/
```

---

## Production-Like Compose Verification

To inspect hardened production Compose configurations:

```bash
docker compose --env-file .env.production.example -f docker-compose.prod.yml config
```

Baseline production hardening checks:
- `APP_ENV=production`
- `AUTH_MODE=jwks` with `AUTH_LOCAL_TOKENS_ENABLED=false`
- `RELIABILITY_STORE=redis`
- `ARTIFACT_BACKEND=s3`
- `SCHEDULER_ENABLED=true`
- `DLP_ENABLED=true`
- `REMOTE_TAKEOVER_ENABLED=true`

---

## Docker Compose Services

| Service | Port | Architectural Role |
| :--- | :--- | :--- |
| `api` | 8000 | FastAPI Control Plane & Operations Center web console |
| `worker` | Internal | Kafka consumer + Playwright multi-engine runner |
| `postgres` | 5432 | Relational database (Tasks, Schedules, Audit Logs) |
| `redis` | 6379 | Reliability store, rate limiter, and distributed locks |
| `kafka` | 9092 | Distributed task event bus (`high`, `queued`, `batch`, `dlq`) |
| `minio` | 9000, 9001 | S3-compatible artifact storage backend |

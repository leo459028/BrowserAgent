from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "browser-agent"
    app_version: str = "1.4.2"
    app_env: str = "local"
    app_log_level: str = "INFO"
    app_secret_key: str = "change-me"
    auth_enabled: bool = True
    auth_mode: str = "local"
    auth_jwt_issuer: str = "browser-agent-local"
    auth_jwt_audience: str = "browser-agent-api"
    auth_jwks_url: str = ""
    auth_oidc_issuer_url: str = ""
    auth_jwks_cache_ttl_seconds: int = 300
    auth_jwks_request_timeout_seconds: int = 5
    auth_token_ttl_seconds: int = 3600
    auth_local_tokens_enabled: bool = True

    # V1.3 OIDC Authorization Code Flow
    auth_oidc_client_id: str = "browser-agent-client"
    auth_oidc_client_secret: str = "client-secret-change-me"
    auth_oidc_redirect_uri: str = "http://localhost:8000/v1/auth/oidc/callback"
    auth_oidc_authorization_endpoint: str = ""
    auth_oidc_token_endpoint: str = ""
    auth_oidc_userinfo_endpoint: str = ""

    # V1.3 Enterprise KMS 信封加密
    kms_provider: str = "local"  # "local" | "aws" | "vault"
    kms_master_key: str = "01234567890123456789012345678901"  # 32-byte string for local AES-256-GCM
    kms_key_id: str = "local-kek-v1"
    kms_region: str = "us-east-1"
    vault_addr: str = "http://localhost:8200"
    vault_token: str = ""

    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = ""
    artifact_backend: str = "local"
    artifact_base_path: str = "/tmp/browser-agent/artifacts"
    reliability_store: str = "memory"

    # V1.3 多優先權佇列與 Worker 資源池
    multi_priority_enabled: bool = True
    queue_high_topic: str = "agent.tasks.high"
    queue_default_topic: str = "agent.tasks.queued"
    queue_batch_topic: str = "agent.tasks.batch"
    worker_pool: str = "default"

    # V1.3 即時廣播與自癒引擎
    live_broadcast_enabled: bool = True
    self_healing_enabled: bool = True
    self_healing_threshold: float = 0.75

    # V1.4 雙向即時遠端接管 (HITL)
    remote_takeover_enabled: bool = True
    remote_takeover_timeout_seconds: int = 300

    # V1.4 跨瀏覽器矩陣執行 (Cross-Browser Grid)
    default_browser_engine: str = "chromium"  # "chromium" | "firefox" | "webkit"

    # V1.4 零信任動態情境資料防洩 (Zero-Trust DLP)
    dlp_enabled: bool = True
    dlp_mask_passwords: bool = True
    dlp_redact_tokens: bool = True

    # V1.4 多叢集排程同盟與高可用容災 (Multi-Cluster Federation)
    federation_enabled: bool = True
    federation_node_id: str = "node-local-1"
    federation_region: str = "local-dev"
    federation_heartbeat_interval_seconds: int = 10
    federation_lease_ttl_seconds: int = 30

    allowlist_domains: str = "example.com,example.org"
    task_create_rate_limit_per_minute: int = 60
    idempotency_ttl_seconds: int = 86400
    task_lock_ttl_seconds: int = 300
    max_task_retries: int = 2
    task_timeout_seconds: int = 120
    browser_headless: bool = True
    worker_service_id: str = "worker-local"
    dlq_topic: str = "agent.tasks.dlq"

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio12345"
    minio_bucket: str = "browser-agent"

    otel_enabled: bool = False
    otel_service_name: str = "browser-agent"
    otel_exporter_otlp_endpoint: str = ""
    otel_resource_attributes: str = "service.namespace=browser-agent"
    otel_propagators: str = "tracecontext,baggage"

    alert_webhook_url: str = ""
    alert_dlq_threshold: int = 5
    alert_auth_failures_threshold: int = 10
    alert_quarantine_threshold: int = 3
    alert_webhook_timeout_seconds: float = 3.0

    worker_record_video_default: bool = True
    scheduler_enabled: bool = True

    @property
    def allowlist_domain_set(self) -> set[str]:
        return {d.strip() for d in self.allowlist_domains.split(",") if d.strip()}

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

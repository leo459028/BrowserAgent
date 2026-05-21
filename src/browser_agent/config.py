from functools import lru_cache
from pydantic_settings import BaseSettings, SettingsConfigDict

class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=".env", extra="ignore")

    app_name: str = "browser-agent"
    app_env: str = "local"
    app_log_level: str = "INFO"
    app_secret_key: str = "change-me"
    auth_enabled: bool = True
    auth_jwt_issuer: str = "browser-agent-local"
    auth_jwt_audience: str = "browser-agent-api"
    auth_token_ttl_seconds: int = 3600
    auth_demo_tokens_enabled: bool = True

    database_url: str = "postgresql+psycopg://agent:agent@localhost:5432/agent"
    redis_url: str = "redis://localhost:6379/0"
    kafka_bootstrap_servers: str = "localhost:9092"
    artifact_base_path: str = "/tmp/browser-agent/artifacts"

    allowlist_domains: str = "example.com,example.org"
    max_task_retries: int = 2
    task_timeout_seconds: int = 120
    browser_headless: bool = True

    minio_endpoint: str = "localhost:9000"
    minio_access_key: str = "minio"
    minio_secret_key: str = "minio12345"
    minio_bucket: str = "browser-agent"

    @property
    def allowlist_domain_set(self) -> set[str]:
        return {d.strip() for d in self.allowlist_domains.split(",") if d.strip()}

@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()

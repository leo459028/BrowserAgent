from pathlib import Path


def test_production_compose_and_env_templates_exist_with_v11_defaults():
    env_text = Path(".env.production.example").read_text(encoding="utf-8")
    compose_text = Path("docker-compose.prod.yml").read_text(encoding="utf-8")

    assert "APP_VERSION=1.1.0" in env_text or "APP_VERSION=1.2.0" in env_text
    assert "APP_ENV=production" in env_text
    assert "AUTH_MODE=jwks" in env_text
    assert "AUTH_LOCAL_TOKENS_ENABLED=false" in env_text
    assert "RELIABILITY_STORE=redis" in env_text
    assert "ARTIFACT_BACKEND=s3" in env_text
    assert "OTEL_ENABLED=false" in env_text
    assert "OTEL_PROPAGATORS=tracecontext,baggage" in env_text
    assert "api:" in compose_text
    assert "worker:" in compose_text
    assert "env_file:" in compose_text
    assert ".env.production.example" in compose_text

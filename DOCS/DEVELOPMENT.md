# Development

## Tech Stack

- Python 3.12+ in Docker image。
- FastAPI。
- Jinja2。
- Pydantic v2 / pydantic-settings。
- SQLAlchemy 2.x。
- PostgreSQL 16。
- Kafka via `confluent-kafka`。
- Redis client package。
- Playwright sync API。
- Prometheus client。
- Alembic。
- pytest。

Windows host 目前可用 Python 3.11 跑測試；Docker image 使用 Python 3.12。

## Local Setup

建議使用專案 `.venv`：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

啟動 API：

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m uvicorn browser_agent.app:app --host 127.0.0.1 --port 8000
```

Dashboard：

```text
http://127.0.0.1:8000/demo
```

## Tests

`pyproject.toml` 已設定：

```toml
pythonpath = ["src", "."]
```

Host 測試：

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker 測試：

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

主要 test files：

- `tests/test_policy.py`：domain allowlist 與 policy decision。
- `tests/test_evaluator.py`：final URL、HTML、artifact、expected-domain evaluator。
- `tests/test_v01_demo.py`：Dashboard rendering、artifact serialization、task list API、audit API。
- `tests/test_v02_lifecycle.py`：pending approval、blocked domain、high-risk approval、sensitive approval、queued approval、failed metadata/audit。
- `tests/test_v03_artifacts.py`：artifact metadata、local backend、redaction metadata、serialization、tenant access check。
- `tests/test_v04_planner.py`：Planner schema validation、required fields、deterministic fallback、fallback metadata。
- `tests/test_v04_skillhub.py`：SkillHub resolution、requested version、missing skill builtin fallback。
- `tests/test_v05_auth_rbac.py`：JWT auth、RBAC deny/pass、authenticated approval actor、admin SkillHub registration、artifact tenant check。
- `tests/test_v06_reliability.py`：idempotency、rate limit、reliability status、worker lock、DLQ publish/replay、Dashboard v0.6 rendering。
- `tests/test_worker_runner.py`：worker task ID coercion、retry/backoff、failed marking。

最新實測結果請看 [TEST_REPORT.md](./TEST_REPORT.md)。

## Docker Compose

啟動：

```powershell
docker compose up -d --build
```

檢查：

```powershell
docker compose ps
```

API 與 worker container 啟動時會執行：

```text
python scripts/bootstrap.py
```

Bootstrap 會建立 database schema、demo tenant/users，並在 `BOOTSTRAP_KAFKA_TOPICS=true` 時建立 Kafka topics。

若 Kafka/Zookeeper 遇到 stale broker session，可先嘗試：

```powershell
docker compose restart zookeeper kafka api worker
```

## Development Notes

- Active artifact backend 是 `LocalArtifactStore`。
- MinIO 目前在 Compose 中存在，但尚未作為 active artifact backend。
- Redis 目前在 Compose 中作為 v0.6 reliability store，用於 task create rate limiting 與 worker task locks；host/unit tests 預設 memory store。
- Kafka 與 Playwright lazy imports 方便 unit tests 不需 native services。
- `/metrics` 是 process-local；API `/metrics` 不包含 worker process counters。
- v0.6 local JWT 使用 `APP_SECRET_KEY` 簽章；正式部署不可使用預設值。

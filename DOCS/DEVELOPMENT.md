# Development

## Tech Stack

- Python 3.12+ in Docker image
- FastAPI
- Jinja2
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL 16
- Kafka via `confluent-kafka`
- Redis client package
- Playwright sync API
- Prometheus client
- Alembic
- pytest

Windows host 目前可用 Python 3.11 執行測試；Docker image 使用 Python 3.12。

## Local Setup

建議使用專案 `.venv`，避免誤用沒有安裝 `psycopg` 的全域 Python：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

本機啟動 API：

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

目前主要 test files：

- `tests/test_policy.py`：domain allowlist 與 policy decision。
- `tests/test_evaluator.py`：final URL、HTML、artifact、expected-domain evaluator。
- `tests/test_v01_demo.py`：approval demo identity、artifact serialization、Dashboard route、task list API、audit API。
- `tests/test_v02_lifecycle.py`：pending approval、blocked domain、high-risk approval、sensitive approval、queued approval、failed metadata/audit。
- `tests/test_v03_artifacts.py`：artifact metadata、local backend、redaction metadata、serialization、tenant access check。
- `tests/test_v04_planner.py`：Planner schema validation、required fields、deterministic fallback、fallback metadata。
- `tests/test_v04_skillhub.py`：SkillHub resolution、requested version、missing skill builtin fallback。
- `tests/test_worker_runner.py`：worker task ID coercion、retry/backoff、failed marking。

最新實測結果請見 [TEST_REPORT.md](./TEST_REPORT.md)。

## Docker Compose

啟動：

```powershell
docker compose up -d --build
```

狀態：

```powershell
docker compose ps
```

API 與 worker container command 都會先跑：

```text
python scripts/bootstrap.py
```

Bootstrap 會建立 database schema、demo tenant/user，並在 `BOOTSTRAP_KAFKA_TOPICS=true` 時建立 Kafka topics。

若 Kafka/Zookeeper 重啟後遇到 stale broker session，可先不刪 volume，執行：

```powershell
docker compose restart zookeeper kafka api worker
```

## Development Notes

- Active artifact backend 是 `LocalArtifactStore`。
- MinIO 目前存在於 Compose，但尚未成為 active artifact backend。
- Redis 目前存在於 Compose，尚未用於 locks、dedupe 或 rate limiting。
- Kafka 與 Playwright lazy imports 是為了讓 unit tests 不需要 native services 即可 import module。
- `MAX_TASK_RETRIES` 是 Settings 欄位，但目前 worker consumer 的 `_run_task_with_retries()` 預設使用 3 次；尚未把設定值接進 consumer main loop。
- `/metrics` 是 process-local；API `/metrics` 不包含 worker process counters。

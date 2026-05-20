# Development

## Tech Stack

- Python 3.12+ in Docker image
- FastAPI
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL 16
- Kafka via `confluent-kafka`
- Redis client package
- Playwright sync API
- Prometheus client
- Alembic
- pytest

本機 Windows environment 可以使用 Python 3.11，但 `pyproject.toml` 與 `Dockerfile` 目標是 Python 3.12+。

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Tests

`pyproject.toml` 設定：

```toml
pythonpath = ["src", "."]
```

執行：

```powershell
pytest -q
```

目前 test files：

- `tests/test_policy.py`：allowlist policy。
- `tests/test_evaluator.py`：final URL、HTML、artifact、expected-domain evaluator。
- `tests/test_v01_demo.py`：approval demo identity、artifact serialization、Dashboard route、task list API、audit API。
- `tests/test_v02_lifecycle.py`：pending approval、blocked domain、high-risk approval、sensitive approval、queued approval、failed metadata/audit。
- `tests/test_v03_artifacts.py`：artifact metadata、local backend、redaction metadata、serialization、tenant access check。
- `tests/test_worker_runner.py`：worker task ID coercion、retry/backoff、failed marking。

最新 v0.2/v0.3 驗證報告請見 [TEST_REPORT.md](./TEST_REPORT.md)。

## 本機啟動 API

```powershell
python -m uvicorn browser_agent.app:app --reload --host 0.0.0.0 --port 8000
```

Dashboard：

```text
http://localhost:8000/demo
```

注意：如果 Docker Compose 也 publish port `8000`，測試 Docker 的 `http://127.0.0.1:8000` 前，請先停止本機 uvicorn。

## Docker Compose

```powershell
docker compose up -d --build
```

在 API container 內執行 tests：

```powershell
docker compose exec -T api pytest -q
```

## DB Migration 與 Bootstrap

Alembic 已設定，但 local Compose 主要使用：

```powershell
docker compose exec api python scripts/bootstrap.py
```

Bootstrap script 會建立 schema、seed demo tenant/user，並在設定啟用時建立 Kafka topics。

## Development Notes

- Redis 與 MinIO 存在於 Compose，但目前不是 core task/artifact flow 的 active dependency。
- Active artifact backend 是 `LocalArtifactStore`。
- Kafka 與 Playwright 盡量使用 lazy imports，避免 unit tests 在 import 階段就需要 native packages。
- Approval 會在 `tasks.approved_by` 儲存 user UUID，在 `approvals.approved_by` 儲存 display label。
- `/metrics` 是 process-local。

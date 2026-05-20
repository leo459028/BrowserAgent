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

注意：本機 `.venv` 目前可用 Python 3.11 跑測試，但 `pyproject.toml` 與 Dockerfile
目標是 Python 3.12+。

## Local Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
python -m playwright install chromium
```

## Tests

Windows 建議使用：

```powershell
$env:PYTHONPATH = "src;."
.\.venv\Scripts\python.exe -m pytest
```

目前測試覆蓋：

- `tests/test_policy.py`：allowlist policy。
- `tests/test_evaluator.py`：final URL、HTML、artifact、expected domain evaluator。
- `tests/test_v01_demo.py`：approval demo UUID/label、artifact serialization、Dashboard route、task list API、audit API。
- `tests/test_v02_lifecycle.py`：pending approval、blocked domain、high-risk approval、sensitive approval、queued approval、failed metadata/audit。
- `tests/test_worker_runner.py`：worker retry/backoff 與 failed marking。

## Run API Locally

```powershell
$env:PYTHONPATH = "src;."
.\.venv\Scripts\python.exe -m uvicorn browser_agent.app:app --reload --host 0.0.0.0 --port 8000
```

Dashboard:

```text
http://localhost:8000/demo
```

## Docker Compose

完整本機 stack：

```powershell
docker compose up --build -d
```

端到端驗證請參考 [RUNBOOK.md](./RUNBOOK.md)。

## DB Migration

Alembic 設定在 `alembic.ini`。本機直接跑時需確認 `sqlalchemy.url` 指向可連線 DB。

```powershell
$env:PYTHONPATH = "src;."
alembic upgrade head
```

Compose 主要透過 `scripts/bootstrap.py` 建立 schema 與 seed demo identity。

## Development Notes

- 不要假設 Redis/MinIO 已接核心流程；目前主要是 compose/config 存在。
- 修改 approval 時，維持 `tasks.approved_by` 保存 user UUID、`approvals.approved_by` 保存顯示 label。
- 修改 lifecycle 時，同步更新 Kafka topics、runbook、observability 與 tests。
- `/metrics` 目前是 process-local；Docker Compose 下 API 不會自動匯總 worker metrics。


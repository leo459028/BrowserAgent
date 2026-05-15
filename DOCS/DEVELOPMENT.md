# 開發指南

## 技術棧

- Python 3.12+
- FastAPI
- Pydantic v2 / pydantic-settings
- SQLAlchemy 2.x
- PostgreSQL 16
- Kafka via `confluent-kafka`
- Redis client package 已安裝但目前未使用
- Playwright sync API
- Prometheus client
- Alembic
- pytest

## 安裝

本機 Python 環境：

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
python -m pip install -r requirements.txt
```

若要執行 browser runner，還需要安裝 Playwright browser：

```powershell
python -m playwright install chromium
```

## 執行測試

```powershell
$env:PYTHONPATH = "src"
pytest -q
```

目前測試覆蓋：

- `tests/test_policy.py`：未 allowlist domain 會被 policy 擋下。
- `tests/test_evaluator.py`：有 final URL、HTML、artifact、expected domain 時 evaluator 通過。

建議新增測試：

- API create task 成功與 blocked cases。
- fixed tenant/user seed 缺失時的明確錯誤。
- approval 欄位型別修正後的 approval flow。
- BrowserRunner allowlist blocking。
- Worker 對 approved/created/blocked/completed status 的處理。
- Artifact row 寫入與 checksum。

## 執行 API

```powershell
$env:PYTHONPATH = "src"
uvicorn browser_agent.app:app --reload --host 0.0.0.0 --port 8000
```

或使用 Makefile：

```powershell
make run
```

在 Windows 沒有 make 時，直接使用 uvicorn 指令。

## 格式/靜態檢查

目前 `Makefile` 的 `fmt` 與 `lint` 都是 compileall：

```powershell
python -m compileall src tests worker alembic
```

這只能檢查語法，不會做格式化或 lint。建議後續引入：

- `ruff`：lint + import sorting
- `black` 或 ruff format：格式化
- `mypy` 或 pyright：型別檢查

## DB migration

Alembic 設定在 `alembic.ini`，預設連到 localhost：

```powershell
$env:PYTHONPATH = "src"
alembic upgrade head
```

Compose 內 API/worker 使用 `postgres` hostname；本機 alembic 使用 localhost。若在不同環境執行，需確認 `sqlalchemy.url` 或環境變數一致。

## 開發注意事項

- 不要把藍圖中的完整狀態機當成已實作；目前狀態流較短。
- 不要直接假設 Redis/MinIO 已接上核心流程；目前只是 compose/config 存在。
- 修改 approval 時，先處理 `tasks.approved_by` 型別不一致。
- 修改 Dockerfile 時，補上 Playwright browser install，否則 worker 很可能無法啟動 Chromium。
- 新增任何 task lifecycle 事件時，同步更新 Kafka topics、runbook、observability 與 tests。

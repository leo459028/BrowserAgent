# Enterprise Browser Agent Platform

BrowserAgent 是一個 production-grade 的 Browser Agent scaffold。v0.4 目前聚焦在 Planner 輸出驗證、SkillHub resolver 整合、Dashboard 查詢與測試能力，以及可稽核的 fallback 行為。

## 目前能力

- FastAPI control plane：task、approval、artifact、skill API。
- PostgreSQL system of record：tasks、steps、artifacts、evaluations、audit logs。
- Kafka event bus：建立與核准 task 後發布事件，worker 消費 queued task。
- Playwright browser runner：支援 `goto`、`click`、`fill`、`press`、`wait`、`extract_text`、`screenshot`。
- Policy engine：domain allowlist、risk level、敏感指令與 prompt-injection 檢查。
- v0.3 artifact governance：local artifact backend、SHA-256、content type、size、retention、redaction metadata、tenant access check。
- v0.4 Planner/SkillHub：Planner schema validation、deterministic fallback、SkillHub capability resolution metadata。
- `/demo` v0.4 Dashboard：建立測試 task、核准 task、查詢 Planner/SkillHub、audit、metrics、steps、evaluation、artifacts。

## 快速啟動

```powershell
cp .env.example .env
docker compose up -d --build
```

Dashboard：

```text
http://localhost:8000/demo
```

API health check：

```powershell
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

## v0.4 Dashboard 測試方式

先用專案 `.venv` 啟動 API，避免誤用沒有安裝 `psycopg` 的全域 Python：

```powershell
$env:PYTHONPATH='src'
.\.venv\Scripts\python.exe -m uvicorn browser_agent.app:app --host 127.0.0.1 --port 8000
```

如果尚未安裝相依套件：

```powershell
.\.venv\Scripts\python.exe -m pip install -r requirements.txt
```

測試步驟：

1. 開啟 `http://127.0.0.1:8000/demo`。
2. 選擇 `Normal planner task` 並建立 task；剛建立時進入 `pending_approval` 是正常行為。
3. 對 `pending_approval` task 點擊 `Approve selected`，等待 worker 完成後確認 Planner validation 顯示 pass，並檢查 screenshot/html artifact。
4. 選擇 `Fallback planner task`，建立並 approve task，確認 validation errors 與 fallback 狀態可見。
5. 點擊 `Register demo skills`，再執行 `SkillHub resolved task`，確認 `browser.goto` 與 `browser.screenshot` 顯示 resolved。
6. 在未註冊對應 skill 的情境下執行 `SkillHub missing task`，確認仍可使用 builtin browser action fallback。

## 建立 Task 範例

```powershell
curl -X POST http://localhost:8000/v1/tasks `
  -H 'Content-Type: application/json' `
  -d '{
    "title":"Capture example",
    "instructions":"Open the allowlisted site and capture a screenshot.",
    "priority":1,
    "risk_level":"low",
    "metadata":{
      "domains":["example.com"],
      "start_url":"https://example.com",
      "expected_domain":"example.com"
    }
  }'
```

核准 task：

```powershell
curl -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve `
  -H 'Content-Type: application/json' `
  -d '{"approved_by":"ops@example.com","note":"Approved for local v0.4 test"}'
```

## 本機測試

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker 環境可用時：

```powershell
docker compose exec -T api pytest -q
```

實際驗證結果請見 [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)。

## 專案結構

```text
src/browser_agent/
  api.py
  app.py
  llm.py
  planner.py
  runner.py
  skillhub.py
  services/
worker/
tests/
DOCS/
alembic/
sql/
```

## 文件

- [DOCS/API.md](DOCS/API.md)
- [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)
- [DOCS/IMPLEMENTATION_STATUS.md](DOCS/IMPLEMENTATION_STATUS.md)
- [DOCS/ROADMAP.md](DOCS/ROADMAP.md)
- [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)

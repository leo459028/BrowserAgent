# Test Report

最後更新：2026-05-21

## 摘要

v0.4 Planner/SkillHub Dashboard 實作後，已完成 host 端單元、整合、compile、diff check、Docker container pytest、Docker API health/readiness、Dashboard smoke test，以及 Normal/Fallback/SkillHub resolved E2E。

## 文件同步檢查

2026-05-21 重新檢查所有 Markdown 文件後，已同步更新：

- `README.md`
- `DOCS/OVERVIEW.md`
- `DOCS/API.md`
- `DOCS/ARCHITECTURE.md`
- `DOCS/CONFIGURATION.md`
- `DOCS/DATA_MODEL.md`
- `DOCS/DEVELOPMENT.md`
- `DOCS/IMPLEMENTATION_STATUS.md`
- `DOCS/OBSERVABILITY.md`
- `DOCS/ROADMAP.md`
- `DOCS/RUNBOOK.md`
- `DOCS/SECURITY_AND_POLICY.md`
- `DOCS/USE_CASES.md`
- `scripts/README.md`

文件掃描確認未殘留亂碼、舊版 Dashboard 標題、v0.4 未完成敘述、舊 Planner/SkillHub 狀態、舊測試數量等過期內容。同步後重新執行：

```text
pytest -q -> 31 passed, 2 warnings
python -m compileall src tests worker alembic -> passed
git diff --check -> passed
docker compose exec -T api pytest -q -> 31 passed
```

## Host 測試結果

### `pytest -q`

結果：

```text
31 passed, 2 warnings in 1.49s
```

Warnings：
- `pythonjsonlogger.jsonlogger` deprecation warning。
- `.pytest_cache` 寫入 permission warning：測試結果通過，但 sandbox 無法寫入部分 pytest cache 檔案。

### `python -m compileall src tests worker alembic`

結果：

```text
exit code 0
```

輸出顯示 `src`、`tests`、`worker`、`alembic` 皆完成 compile scan，未發現語法錯誤。

### `git diff --check`

結果：

```text
exit code 0
```

表示目前 diff 沒有 trailing whitespace 或 patch 格式問題。

### Targeted v0.4 tests

Command：

```powershell
pytest tests\test_v04_planner.py tests\test_v04_skillhub.py tests\test_v01_demo.py -q
```

結果：

```text
13 passed, 2 warnings in 1.42s
```

## v0.4 Test Coverage

### `tests/test_v04_planner.py`

覆蓋：
- valid Planner output 通過 schema validation。
- 每個 step 保留 JSON-serializable `input_data`。
- 缺少必要欄位時記錄 validation error。
- deterministic fallback 在有 `metadata.start_url` 時產生 `goto + screenshot`。
- invalid Planner output 會讓 metadata 記錄 `fallback_used=true` 與錯誤摘要。

### `tests/test_v04_skillhub.py`

覆蓋：
- active skill 可解析為 `resolved=true`。
- step 指定 `skill_version` 時，resolver 使用指定版本。
- 找不到 skill 時不阻止 step，並標示 builtin fallback metadata。

### `tests/test_v01_demo.py`

新增覆蓋：
- `/demo` 顯示 `Browser Agent v0.4 Dashboard`。
- Dashboard HTML 包含 `Planner`、`SkillHub`、`fallback`、`validation`。
- 既有 artifact query、audit、metrics、task list API 測試維持通過。

## Docker 驗證

### `docker compose up -d --build`

結果：

```text
Image browseragent-api Built
Image browseragent-worker Built
Container browseragent-postgres-1 Started
Container browseragent-redis-1 Started
Container browseragent-kafka-1 Started
Container browseragent-api-1 Started
Container browseragent-worker-1 Started
```

第一次啟動後 Kafka 因 Zookeeper 舊 session 出現 `NodeExistsException`，API bootstrap 暫時等待 Kafka。未刪除任何 volume，執行：

```powershell
docker compose restart zookeeper kafka api worker
```

重啟後 Kafka、API、worker 皆正常啟動。

### `docker compose exec -T api pytest -q`

結果：

```text
31 passed in 1.17s
```

### API readiness

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/healthz
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/readyz
```

結果：

```json
{"status":"ok"}
{"status":"ready"}
```

## Dashboard Smoke Test

HTTP 驗證：

```powershell
Invoke-WebRequest -UseBasicParsing http://127.0.0.1:8000/demo
```

頁面文字檢查結果：

```text
PASS Browser Agent v0.4 Dashboard
PASS Planner
PASS SkillHub
PASS fallback
PASS validation
PASS Artifact Query
```

Browser 插件驗證限制：
- in-app Browser 開啟 `http://127.0.0.1:8000/demo` 時回報 `net::ERR_BLOCKED_BY_CLIENT`。
- 改用 `http://localhost:8000/demo` 仍回報 `net::ERR_BLOCKED_BY_CLIENT`。
- 因此本次 UI smoke test 以 FastAPI route test 與 HTTP HTML content check 作為證據。

## Docker E2E

### Normal planner task

流程：
- `POST /v1/tasks`
- `POST /v1/tasks/{task_id}/approve`
- polling `GET /v1/tasks/{task_id}`
- 讀取 artifact content endpoint

結果：

```text
final=completed
planner_valid=True
fallback=False
unresolved=2
steps=2
artifacts=2
artifact_types=screenshot,html
evaluation=pass
score=100.0
screenshot content endpoint=200 image/png
html content endpoint=200 text/html; charset=utf-8
```

此情境未先註冊 SkillHub demo skills，因此 `unresolved=2` 是預期結果；runner 使用 builtin browser action fallback。

### Fallback planner task

使用 `metadata.planner_test="invalid"` 觸發 invalid Planner output。

結果：

```text
final=completed
planner_valid=False
fallback=True
errors=1
plan_actions=goto,screenshot
has_fallback_audit=True
```

### SkillHub resolved task

先註冊：
- `browser.goto`
- `browser.screenshot`

結果：

```text
final=completed
unresolved=0
skills=goto:browser.goto:True,screenshot:browser.screenshot:True
all_resolved=True
```

## v0.1-v0.3 Regression Coverage

既有測試維持通過：
- `tests/test_policy.py`
- `tests/test_evaluator.py`
- `tests/test_v01_demo.py`
- `tests/test_v02_lifecycle.py`
- `tests/test_v03_artifacts.py`
- `tests/test_worker_runner.py`

重要回歸點：
- allowlisted task 仍進入 `pending_approval`。
- blocked-domain task 仍進入 `blocked`。
- high-risk 與 sensitive instruction task 仍需要 approval。
- approval 仍將 task 轉為 `queued`。
- failed task 仍寫入 error metadata 與 audit。
- artifact serialization 仍包含 v0.3 governance fields。
- tenant mismatch artifact access 仍回傳 `403`。

## 其他觀察

- Host 端 pytest 仍有 `.pytest_cache` permission warning，測試結果不受影響。
- Docker 初次啟動遇到 Kafka/Zookeeper stale broker session，透過 restart zookeeper/kafka/api/worker 解決，未刪除 volume。

## AGENTS.md 文件規範驗證

日期：2026-05-21

本次新增根目錄 `AGENTS.md`，作為 BrowserAgent 專案通用工作規範。此變更是文件新增，未修改程式碼，因此未重新執行完整 `pytest` 與 `compileall`。

實際驗證結果：

```text
Test-Path AGENTS.md -> True
rg -n "Dashboard|/demo|DOCS/TEST_REPORT\.md|Docker Desktop|繁體中文|migration" AGENTS.md -> found required guidance
git diff --check -> passed
```

驗證重點：
- `AGENTS.md` 已包含規劃方案、實作方案、測試要求、文件同步要求與專案特別注意事項。
- 已明確要求未來規劃需有 UI 或 Dashboard 查詢與測試入口，預設使用 `/demo`。
- 已明確要求實際測試結果寫入 `DOCS/TEST_REPORT.md`。
- 已明確要求 Docker 測試前提醒使用者開啟 Docker Desktop。
- 已明確要求文件使用繁體中文，並與程式碼、路由、欄位、Dashboard 情境與測試數量同步。

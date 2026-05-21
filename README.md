# BrowserAgent

## 一般版

BrowserAgent 是一個讓系統「代替人操作瀏覽器」的基礎平台。你可以把它想成一個受控的瀏覽器助理：它可以開網頁、按照任務步驟操作頁面、截圖、保存網頁內容，最後把結果記錄下來，讓人可以檢查。

它不是單純的自動化腳本，而是比較偏企業使用的雛形平台。重點不是「讓瀏覽器隨便做任何事」，而是讓每個任務都有規則、有審核、有記錄、有產出物，也有錯誤時可以追查的線索。

### 這個專案的作用

v0.4 目前已經能展示一個受控的瀏覽器任務流程：

- 有本機 Dashboard 可以建立任務、核准任務、查看狀態。
- 任務會先進入人工核准，不會建立後就立刻執行。
- 系統會把任務拆成瀏覽器步驟，例如開網頁、等待、截圖。
- 如果系統產生的步驟格式不正確，會改用安全的備用步驟。
- 可以看到每個步驟是否有對應到已註冊的能力。
- 任務完成後會保存截圖和 HTML，方便事後檢查。
- 所有重要狀態會留下紀錄，例如建立、核准、執行、完成、失敗。

v0.5 預計會更靠近正式使用環境，重點會放在登入和權限：

- 加入正式使用者登入。
- 不同角色有不同權限，例如建立任務的人、核准任務的人、管理員。
- 核准紀錄會綁定真實使用者，而不是現在的 demo 使用者。
- Dashboard 的人工核准流程會更接近正式作業。

v1.0 預計會朝 production-ready 平台前進：

- 支援更完整的部署方式，例如 Kubernetes。
- Worker 可以擴充數量，處理更多任務。
- 加入更好的重試、排隊、失敗任務處理。
- 強化瀏覽器執行環境的隔離，降低風險。
- 使用更正式的機密管理方式。
- 加入更完整的監控、告警和追蹤。
- 可能加入瀏覽器操作回放，讓人能看任務怎麼跑。

### 應用場景

- 網頁流程檢查：定期確認某個網站頁面是否能正常打開、內容是否存在、畫面是否和預期相近。
- 網站資料留存：保存活動頁、公告頁、商品頁、價格頁等「當下看到的畫面」作為證據。
- 內部系統操作測試：在受控環境下測試簡單流程，例如打開頁面、檢查正確網域、截圖留存。
- 需要人工核准的自動化：任務先進入 `pending_approval`，由人確認後才排隊執行。
- 瀏覽器自動化平台原型：評估企業內部是否能做一個有規則、有審核、有紀錄的瀏覽器代理平台。

### 不適合的場景

- 不適合直接上正式生產環境；目前仍是 scaffold，不是完整產品。
- 不適合處理高風險操作，例如轉帳、付款、修改帳戶資料、提交法律文件、刪除重要資料。
- 不適合繞過網站規則、破解限制、規避驗證或大量抓取資料。
- 不適合取代完整 QA 自動化平台；大量測試案例、細緻斷言、跨瀏覽器矩陣測試仍需要專門工具。
- 不適合處理需要大量人工判斷的任務，例如複雜內容理解、商業判斷、法律風險審核或圖片語意判斷。

### 相關特性和限制

已有特性：

- 有本機 Dashboard 可以建立、核准、查詢和測試任務。
- 有任務狀態流程，例如 `pending_approval`、`queued`、`executing`、`completed`、`failed`。
- 有 allowlist 機制，非允許網域會被擋下。
- 高風險和敏感指令會要求人工核准。
- 任務會留下 audit 紀錄，方便追蹤發生過什麼事。
- 任務完成後會保存 screenshot 和 HTML。
- Artifact 讀取有基本的 tenant 和檔案路徑檢查。
- Planner 輸出會被檢查，不合格時會使用安全 fallback。
- SkillHub 可以記錄能力是否有被解析到，但目前只做 metadata。

目前限制：

- 尚未有正式登入和角色權限。
- 目前使用固定 demo 使用者。
- Planner 仍是簡單規則，不是外部 LLM。
- SkillHub 目前不執行第三方工具，只記錄解析結果。
- Artifact 目前存在 local filesystem，還沒有真正使用 MinIO/S3。
- Dashboard 是本機測試工具，不是正式營運後台。
- Metrics 是 process-local，不是完整分散式監控。
- Worker retry、DLQ、任務重播、擴充部署都還需要加強。
- 瀏覽器隔離目前是 Docker + Playwright，還不是更強的 sandbox。

白話總結：BrowserAgent 現在適合拿來做「受控瀏覽器自動化平台」的原型和測試。它能展示一個任務從建立、核准、執行、截圖、保存結果到留下紀錄的完整流程。v0.4 的價值在於把任務規劃、備用流程、能力解析和 Dashboard 查詢補起來；v0.5 到 v1.0 則會往登入權限、生產部署、安全隔離、監控和更完整營運能力前進。

## 技術版

BrowserAgent 是一個 production-grade 的 Browser Agent scaffold。v0.4 目前聚焦在 Planner 輸出驗證、SkillHub resolver 整合、Dashboard 查詢與測試能力，以及可稽核的 fallback 行為。

### 目前能力

- FastAPI control plane：task、approval、artifact、skill API。
- PostgreSQL system of record：tasks、steps、artifacts、evaluations、audit logs。
- Kafka event bus：建立與核准 task 後發布事件，worker 消費 queued task。
- Playwright browser runner：支援 `goto`、`click`、`fill`、`press`、`wait`、`extract_text`、`screenshot`。
- Policy engine：domain allowlist、risk level、敏感指令與 prompt-injection 檢查。
- v0.3 artifact governance：local artifact backend、SHA-256、content type、size、retention、redaction metadata、tenant access check。
- v0.4 Planner/SkillHub：Planner schema validation、deterministic fallback、SkillHub capability resolution metadata。
- `/demo` v0.4 Dashboard：建立測試 task、核准 task、查詢 Planner/SkillHub、audit、metrics、steps、evaluation、artifacts。

### 快速啟動

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

### v0.4 Dashboard 測試方式

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

### 建立 Task 範例

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

### 本機測試

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

### 專案結構

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

### 文件

- [DOCS/OVERVIEW.md](DOCS/OVERVIEW.md)
- [DOCS/API.md](DOCS/API.md)
- [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)
- [DOCS/IMPLEMENTATION_STATUS.md](DOCS/IMPLEMENTATION_STATUS.md)
- [DOCS/ROADMAP.md](DOCS/ROADMAP.md)
- [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)

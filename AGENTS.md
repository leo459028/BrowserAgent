# BrowserAgent 專案工作規範

本檔案是給未來在這個 repo 工作的 agent / engineer 使用。請優先遵守這裡的規範，再參考 `README.md` 與 `DOCS/OVERVIEW.md`。

## 適用範圍

這份規範適用整個 BrowserAgent 專案。除非子目錄另有更細的 `AGENTS.md`，否則所有程式碼、測試與文件更新都要遵守本檔案。

## 1. 規劃方案要求

任何新版本、新功能或修正計畫，都必須包含可以查詢與測試的 UI 或 Dashboard 入口。此專案自 V1.0 起預設優先使用 `/operations`（Operations Center，`/demo` 為相容保留）；如果不適合使用 `/operations`，計畫中必須清楚說明替代入口，例如 API smoke test、新的 Dashboard panel，或其他可操作、可查詢、可驗證的介面。

規劃內容至少要包含：

- 功能目標與成功條件。
- UI / Dashboard 如何操作、查詢與驗證。
- API、metadata、資料流或狀態流程是否改變。
- 實作方案與會影響的主要模組。
- 測試項目與實際要執行的命令。
- 實作完成後要更新哪些文件（務必包含 `DOCS/manual_test.md` 與程式碼同步檢查）。
- `DOCS/TEST_REPORT.md` 要寫入哪些實際測試結果。

不要只寫概念或預期結果；要讓下一位工程師可以直接照著做。

## 2. 實作方案要求

實作時優先沿用本專案既有架構：

- API 使用 FastAPI。
- 資料模型使用 SQLAlchemy。
- Dashboard 使用既有 `/demo` Jinja template。
- 背景任務使用 worker 與 Kafka flow。
- Browser automation 使用 Playwright runner。
- 測試使用 pytest。

避免沒有必要的資料表、migration、外部服務或大型抽象。若 v0.5、v1.0 或其他需求確實需要調整資料模型，必須在方案中清楚說明原因、資料相容性、migration / rollback、測試方式與文件同步範圍。小修或延伸既有版本時，優先沿用現有資料流；版本升級需要時可以合理演進。

修改程式碼前，先讀相關檔案與測試。不要回復或刪除使用者既有變更。若工作樹已有 unrelated changes，保留它們，只修改本次任務需要的範圍。

## 3. 測試要求

實作完成後要做完整測試。若需要 Docker，請先提醒使用者開啟 Docker Desktop，再執行 Docker 相關驗證。

基本測試命令：

```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

Docker 可用時再執行：

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

如果涉及 Operations Center 或 task lifecycle，還要驗證：

- `/operations` 是否能正常開啟。
- Operations Center 是否能建立 task。
- `pending_approval` 是否為預期狀態，且選中任務時 `Approve selected` 是否正常亮綠啟用。
- approve 後 worker 是否能消費佇列並完成 task。
- Visual Step Replay（步驟切換、耗時、DOM、截圖預覽）與 Execution Video Replay 播放器是否正常。
- Scheduled Tasks（Cron 解析、搶鎖、Run Now 立即派發、Pause/Resume）是否正常。
- Session Vault（Storage State 檢索、跨任務免登入復用、一鍵 Revoke 撤銷）是否正常。
- Production Alerting Center（7 大規則評估、Webhook 測試派發）與 Trace Inspector（跨進程 Span 階層樹）是否正常。
- Planner / SkillHub / artifact / audit / metrics / DLQ 是否能查詢與操作。
- Normal、Fallback、SkillHub resolved、SkillHub missing 等相關情境是否仍正常。

所有實際測試結果都要寫入 `DOCS/TEST_REPORT.md`。內容要包含執行日期、命令、通過數量、Dashboard / Operations Center 驗證結果、Docker 驗證結果，以及任何限制或已知問題。不能只寫預期結果。

### 新版本人工測試指引與 `manual_test.md` 更新規範（每次迭代必備）

每次新版本完成實作與自動化測試後，**必須向使用者詳細說明「如何做新版本的人工測試」，並同步更新 `DOCS/manual_test.md` 檔**，避免每次迭代都要重複提醒：

1. **說明內容要求**：
   - 啟動與環境準備（Docker Compose 容器啟動、入口網址）。
   - 介面頂部指標與狀態徽章導覽（Alert Badge, K8s Badge, OTLP Badge 等）。
   - 完整 Step-by-Step UI 人工測試步驟（建立、審批、執行、可視化回放、視訊播放、排程巡檢、工作階段治理、追蹤分析、告警測試、DLQ 處理、RBAC 角色隔離防護）。
   - 常見 UI 疑問與機制說明（FAQ，例如防呆按鈕灰色鎖定原因、視訊載入條件等）。
   - 最小合格檢查清單（Checklist）。
   - API 快速自動化檢查腳本（PowerShell / Curl 一鍵驗證命令）。
2. **`DOCS/manual_test.md` 同步更新**：
   - 必須將上述完整指引更新至 `DOCS/manual_test.md`，並同步版本號（如 V1.2）。
   - 確保所有按鈕文字、欄位鍵值與路由完全與現行程式碼和 UI 一致。

## 4. 文件同步要求（每次迭代必備）

測試通過後，**必須全面檢查並確認專案中所有文件是否已經和新版本的程式碼 100% 同步**，嚴禁遺漏：

1. **代碼與文件比對重點**：
   - **API 路由與 HTTP 方法**：端點路徑（例如 `/v1/scheduled-tasks`、`/v1/sessions`）、HTTP 動詞（GET、POST、PATCH、DELETE）與狀態碼。
   - **Request Payload 與 Response Schema**：欄位名稱（如 `task_template`、`is_active`）、資料型別與結構（如 `list[dict]` 陣列）。
   - **資料庫模型**：SQLAlchemy Models 與 Alembic Migration 腳本中定義的資料表、欄位名稱與型別。
   - **Metadata 結構**：Task metadata、Session Artifact metadata、Video metadata 等規格。
   - **UI 元素與按鈕文字**：Operations Center 畫面上的實際按鈕文字（如 `Run Now`、`Revoke`、`Approve selected`）。
   - **安全性與 RBAC 矩陣**：各端點所要求的角色權限（creator, approver, operator, admin）。
   - **測試案例數量**：已通過的測試數量與測試模組清單。

2. **必須保持同步的文件清單**：
   - `README.md`（一般版僅同步版本號文字，技術版全面完整更新）
   - `DOCS/OVERVIEW.md`（文件索引與版本重點）
   - `DOCS/API.md`（所有 API 規格、Payload 與 Response 範例）
   - `DOCS/ARCHITECTURE.md`（架構設計、核心流程與圖資路徑）
   - `DOCS/CONFIGURATION.md`（環境變數與配置項）
   - `DOCS/DATA_MODEL.md`（SQL 表格、欄位型別、Metadata 規格）
   - `DOCS/IMPLEMENTATION_STATUS.md`（已完成清單與版本摘要）
   - `DOCS/ROADMAP.md`（版本演進規劃）
   - `DOCS/RUNBOOK.md`（維運排查與升級步驟）
   - `DOCS/SECURITY_AND_POLICY.md`（安全政策、RBAC 與敏感資源治理）
   - `DOCS/OBSERVABILITY.md`（可觀測性、告警規則與追蹤架構）
   - `DOCS/TEST_REPORT.md`（實際測試數據與報告）
   - `DOCS/USE_CASES.md`（實際業務情境與操作案例）
   - `DOCS/DEVELOPMENT.md`（開發環境與除錯說明）
   - `DOCS/manual_test.md`（新版本人工測試步驟、FAQ 與 Checklist）

文件不得只描述預期行為；必須跟目前程式碼、路由、欄位、metadata、Dashboard 情境、測試數量與限制同步。相關文件要用繁體中文更新，盡量白話易懂，只保留必要英文技術名稱、API route、欄位名稱與指令。

更新 `README.md` 時要特別注意：`一般版` 是給一般讀者看的穩定產品說明，除非使用者明確要求，否則不要改寫、刪減、重排或新增內容；版本升級時只同步必要版本文字，例如把 `v1.0` 改成 `v1.1` 或 `v1.2`。`技術版` 可以依目前程式碼、路由、設定、測試與文件狀態完整更新。

更新文件時，舊內容除非已經錯誤、過期、重複到會造成誤解，或與目前程式碼/路由/欄位/測試結果衝突，否則不要整段刪除或重寫。優先用新增段落、版本小節、狀態註記或「目前限制 / 歷史演進」方式保留脈絡，讓後續工程師可以看出版本如何演進。若確實需要刪除舊內容，請在變更說明中交代原因。

## 5. 專案特別注意事項

- **每次迭代結尾必備動作**：
  1. **檢查所有的文件是否已經和新版本的程式碼同步**（比對路由、欄位、資料模型、UI 按鈕文字與測試數據）。
  2. **向使用者詳細說明如何做新版本的人工測試，並同步更新 `DOCS/manual_test.md` 檔**。
- 根目錄 `README.md` 是主要入口，分成 `一般版` 與 `技術版`；一般版只做版本文字同步，技術版才可完整更新。
- `DOCS/OVERVIEW.md` 是文件索引，不要再新增 `DOCS/README.md`。
- 自 V1.0 起主要營運入口為 `/operations`（Operations Center）；`/demo` 為早期開發測試頁面。
- 若需要生成 AI 圖片資產，例如架構圖、資訊圖、封面圖、UI mockup 或文件插圖，預設使用 ChatGPT Image2 生圖模型；產出後要放入專案適當路徑，並用清楚的用途或版本檔名保存，避免覆蓋仍需保留的舊圖。
- Planner 目前是 heuristic，不接外部 LLM。
- SkillHub 目前聚焦 resolver metadata，不執行第三方未授權 skill。
- 若 Docker Compose 遇到 Kafka / Zookeeper stale session，可優先嘗試：

```powershell
docker compose restart zookeeper kafka api worker
```

- 回覆使用者時，請清楚說明做了什麼、測了什麼、哪些限制仍存在。

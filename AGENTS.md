# BrowserAgent 專案工作規範

本檔案是給未來在這個 repo 工作的 agent / engineer 使用。請優先遵守這裡的規範，再參考 `README.md` 與 `DOCS/OVERVIEW.md`。

## 適用範圍

這份規範適用整個 BrowserAgent 專案。除非子目錄另有更細的 `AGENTS.md`，否則所有程式碼、測試與文件更新都要遵守本檔案。

## 1. 規劃方案要求

任何新版本、新功能或修正計畫，都必須包含可以查詢與測試的 UI 或 Dashboard 入口。此專案目前預設優先使用 `/demo` Dashboard；如果不適合使用 `/demo`，計畫中必須清楚說明替代入口，例如 API smoke test、新的 Dashboard panel，或其他可操作、可查詢、可驗證的介面。

規劃內容至少要包含：

- 功能目標與成功條件。
- UI / Dashboard 如何操作、查詢與驗證。
- API、metadata、資料流或狀態流程是否改變。
- 實作方案與會影響的主要模組。
- 測試項目與實際要執行的命令。
- 實作完成後要更新哪些文件。
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

如果涉及 Dashboard 或 task lifecycle，還要驗證：

- `/demo` 是否能開啟。
- Dashboard 是否能建立 task。
- `pending_approval` 是否為預期狀態。
- approve 後 worker 是否能完成 task。
- Planner / SkillHub / artifact / audit / metrics 是否能查詢。
- Normal、Fallback、SkillHub resolved、SkillHub missing 等相關情境是否仍正常。

目前 v0.4 中，Normal planner task 建立後進入 `pending_approval` 是正常行為；Planner metadata 通常會在 approve 後，由 worker 執行 task 時才出現。這是目前版本的行為說明，不是限制未來版本的規則。

所有實際測試結果都要寫入 `DOCS/TEST_REPORT.md`。內容要包含執行日期、命令、通過數量、Dashboard 驗證結果、Docker 驗證結果，以及任何限制或已知問題。不能只寫預期結果。

## 4. 文件同步要求

測試通過後，必須比對程式碼與文件是否同步。相關文件要用繁體中文更新，盡量白話易懂，只保留必要英文技術名稱、API route、欄位名稱與指令。

常見需要同步的文件：

- `README.md`
- `DOCS/OVERVIEW.md`
- `DOCS/API.md`
- `DOCS/ARCHITECTURE.md`
- `DOCS/DATA_MODEL.md`
- `DOCS/IMPLEMENTATION_STATUS.md`
- `DOCS/ROADMAP.md`
- `DOCS/RUNBOOK.md`
- `DOCS/SECURITY_AND_POLICY.md`
- `DOCS/TEST_REPORT.md`
- `DOCS/USE_CASES.md`

文件不得只描述預期行為；必須跟目前程式碼、路由、欄位、metadata、Dashboard 情境、測試數量與限制同步。

更新 `README.md` 時要特別注意：`一般版` 是給一般讀者看的穩定產品說明，除非使用者明確要求，否則不要改寫、刪減、重排或新增內容；版本升級時只同步必要版本文字，例如把 `v1.0` 改成 `v1.1`。`技術版` 可以依目前程式碼、路由、設定、測試與文件狀態完整更新。

更新文件時，舊內容除非已經錯誤、過期、重複到會造成誤解，或與目前程式碼/路由/欄位/測試結果衝突，否則不要整段刪除或重寫。優先用新增段落、版本小節、狀態註記或「目前限制 / 歷史演進」方式保留脈絡，讓後續工程師可以看出版本如何演進。若確實需要刪除舊內容，請在變更說明中交代原因。

## 5. 專案特別注意事項

- 根目錄 `README.md` 是主要入口，分成 `一般版` 與 `技術版`；一般版只做版本文字同步，技術版才可完整更新。
- `DOCS/OVERVIEW.md` 是文件索引，不要再新增 `DOCS/README.md`。
- `/demo` 是本機測試 Dashboard，不是正式 production operator UI。
- Planner 目前是 heuristic，不接外部 LLM。
- SkillHub v0.4 只做 resolver metadata，不執行第三方 skill。
- 若 Docker Compose 遇到 Kafka / Zookeeper stale session，可優先嘗試：

```powershell
docker compose restart zookeeper kafka api worker
```

- 回覆使用者時，請清楚說明做了什麼、測了什麼、哪些限制仍存在。

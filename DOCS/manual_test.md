# V1.1 Operations Center Manual Test

本文件說明如何手動驗證 BrowserAgent V1.1 Operations Center。

## 啟動

```powershell
docker compose up -d --build
```

開啟：

```text
http://127.0.0.1:8000/operations
```
> **提示**：系統具備自動容錯轉址，無論輸入 `http://localhost:8000/operations`、`http://localhost:8000/operation` 或首頁根路徑 `http://localhost:8000/`，皆會自動重定向至 Operations Center。

## 完整人工測試流程（Step-by-Step UI Guide）

以下提供維運人員與測試工程師在瀏覽器中進行完整人工功能測試的標準步驟：

### 步驟 1：建立待審核任務（Create Task）
1. 開啟頁面後，將頁面捲動至左側中段的 **`Create Task`** 卡片。
2. 於 `Scenario` 下拉選單選擇 `Normal planner task`（或保留預設 Payload）。
3. 點擊深綠色的 **`Create task`** 按鈕。

### 步驟 2：觀察待審核狀態與審批按鈕啟用
1. 任務建立成功後，左下角的 **Recent Tasks** 列表頂部會出現這筆新任務，狀態標籤顯示為黃色的 **`PENDING_APPROVAL`**。
2. 點選該任務，右上方 Task Detail 會更新其任務詳情。
3. 此時，右上角的 **`Approve selected`** 按鈕會**立即由灰色鎖定狀態切換為亮綠色啟用狀態**（滑鼠懸停顯示「Click to approve this task」）。

### 步驟 3：執行人工審核與觀察執行流程
1. 點擊右上角亮綠色的 **`Approve selected`** 按鈕進行審核。
2. 任務狀態會即時躍遷：`queued` ➜ `executing`。
3. 背景的 Worker 將消費 Kafka 訊息並啟動 Playwright 瀏覽器執行網頁動作。約 3~8 秒後，任務狀態自動更新為綠色的 **`COMPLETED`**。
4. 此時由於任務已執行完畢，右上角的 `Approve selected` 按鈕會**自動恢復為灰色鎖定狀態**，防止重複審查。

### 步驟 4：驗證視覺化步驟回放（Visual Step Replay）
1. 任務完成後，檢視右下角的 **`Visual Step Replay & Replay Timeline`** 區塊。
2. 上方會載入步驟分頁按鈕，例如 `[Step 1: goto ✓]` 與 `[Step 2: screenshot ✓]`。
3. 點擊 **`Step 2: screenshot`** 分頁標籤：
   - **左側步驟詳情**：顯示動作類型（`screenshot`）、耗時毫秒（例如 `598.8 ms`）、對應的 Span ID 與 DOM 摘要。
   - **右側截圖預覽**：直接呈現該步驟所捕獲的網頁畫面縮圖，點擊縮圖可在新分頁開啟完整高解析度原圖。
4. 點擊下方折疊的 `▶ Raw Timeline Events`，可查閱包含審計紀錄、步驟與評估結果之向後相容時間線。

### 步驟 5：驗證端到端分散式追蹤（Trace Inspector）
1. 在 Task Detail 或 Replay 標題旁，複製該任務的 **`Trace ID`**（32 碼十六進位字串）。
2. 捲動至左側的 **`Observability`** 區塊，找到 **`Trace Inspector`** 輸入框。
3. 貼上 Trace ID 並點擊 **`Lookup`** 按鈕。
4. 下方將展開完整的 Span 樹狀追蹤圖，清晰展示 API 進入點、Kafka 發布、Worker 執行以及各瀏覽器步驟的執行耗時與狀態。

### 步驟 6：驗證告警中心與按鈕互動反饋
1. **重新整理反饋**：點擊右上角的 **`Refresh`** 按鈕，按鈕會即時切換為 `Refreshing...` ➜ `Refreshed ✓`，並重新載入所有最新指標。
2. **註冊技能反饋**：點擊右上角的 **`Register built-in skills`** 按鈕，按鈕會切換為 `Registering...` ➜ `Registered ✓`，並於 Create Task 下方顯示註冊完成提示。
3. **測試告警通道派發**：在左側 **`Production Alerting Center`** 卡片中，點擊 **`Test Dispatch`** 按鈕，輸入測試備註後確認，系統將發送非阻塞測試 Webhook 並顯示派發審計紀錄。

---

## 常見 UI 疑問與機制說明（FAQ）

### Q1：右上角的 `Approve selected` 按鈕是灰色的，點不下去是正常的嗎？
**答：完全正常！這是系統安全防護設計。**
- `Approve selected` 專門用於審批狀態為 **`pending_approval`（待審核）** 的任務。
- 當尚未選中任務，或目前選中的任務已經是 **`COMPLETED`（已完成）**、`FAILED`、`QUEUED` 時，系統會自動禁用（disabled 變灰）該按鈕，避免維運人員對已經執行完成的任務重複點擊核准。

### Q2：右上角的 `Refresh` 與 `Register built-in skills` 按鈕點擊後沒有彈窗？
**答：按鈕均具備就地互動文字反饋與背景非同步處理機制。**
- 點擊 `Refresh` 會觸發全面背景重新拉取，按鈕文字會切換為 `Refreshing...` ➜ `Refreshed ✓`。
- 點擊 `Register built-in skills` 會在後端註冊同租戶 SkillHub 技能，完成後按鈕切換為 `Registered ✓`。

---

## 最小合格檢查清單（Checklist）

- 頁面標題顯示 `Browser Agent v1.1 Operations Center`，右上角帶有 `System Alert Badge`。
- `Production Alerting Center` 可載入，顯示 7 大規則狀態指標與 Webhook 指示燈。
- 管理員點選 `Test Dispatch Webhook` 可觸發測試推播與成功提示。
- `Trace Inspector` 輸入任一任務的 Trace ID，點選 `Inspect Trace` 可展開階層式 Spans 追蹤樹。
- `Operations Readiness` 與 `Production Readiness` 正確顯示。
- `Artifact Backend` 在 Docker Compose 顯示 `s3`。
- `Identity / RBAC` 可切換角色（creator, approver, operator, admin）。
- `Try operator create` 顯示 `403`。
- `Normal planner task` 可建立（pending_approval）、核准（queued）、完成（completed）。
- 右側 `Visual Step Replay` 顯示步驟分頁標籤（Step 1, Step 2 ...），點選即時預覽步驟耗時、DOM 摘要與截圖縮圖。
- 點選截圖縮圖可放大檢視或開啟原始解析度 Artifact。
- 下方折疊 `Replay Timeline` 完整保留歷史 audit 與步驟時間線。
- `Refresh DLQ` 可查 failed tasks，`Bulk DLQ replay` 可操作 non-quarantined tasks。

## API 快速檢查

```powershell
# 1. 取得 operator token
$operator = Invoke-RestMethod -Method Post `
  -Uri http://127.0.0.1:8000/v1/auth/local-token `
  -ContentType "application/json" `
  -Body '{"role":"operator"}'
$headers = @{ Authorization = "Bearer $($operator.access_token)" }

# 2. 檢查 Readiness 與 7 大維運告警
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/readiness -Headers $headers
Invoke-RestMethod -Method Get -Uri http://127.0.0.1:8000/v1/ops/alerts -Headers $headers

# 3. 建立並核准 Task，取得 task_id 與 trace_id 驗證 Replay 與 Trace
$creator = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"creator"}'
$task = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/tasks -Headers @{ Authorization = "Bearer $($creator.access_token)" } -ContentType "application/json" -Body '{"title":"Test","instructions":"Capture","priority":1,"risk_level":"low","metadata":{"domains":["example.com"],"start_url":"https://example.com"}}'

$approver = Invoke-RestMethod -Method Post -Uri http://127.0.0.1:8000/v1/auth/local-token -ContentType "application/json" -Body '{"role":"approver"}'
Invoke-RestMethod -Method Post -Uri "http://127.0.0.1:8000/v1/tasks/$($task.task_id)/approve" -Headers @{ Authorization = "Bearer $($approver.access_token)" }

# 等待 Worker 執行完成後檢查 Replay 與 Traces
Start-Sleep -Seconds 5
$replay = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/tasks/$($task.task_id)/replay" -Headers $headers
$trace = Invoke-RestMethod -Method Get -Uri "http://127.0.0.1:8000/v1/ops/traces/$($task.correlation_id)" -Headers $headers
```

# V0.5 Dashboard Manual Test

本文件說明如何手動驗證 BrowserAgent v0.5 Dashboard。重點是「在 `/demo` 上怎麼點、預期看到什麼」。更完整的 API smoke 與 Docker troubleshooting 請參考 [RUNBOOK.md](./RUNBOOK.md)；實際測試結果請記錄到 [TEST_REPORT.md](./TEST_REPORT.md)。

## 1. 前置條件

請先確認 Docker Desktop 已啟動。

在專案根目錄執行：

```powershell
docker compose up -d --build
```

確認 API health 與 readiness：

```powershell
curl.exe http://127.0.0.1:8000/healthz
curl.exe http://127.0.0.1:8000/readyz
```

預期結果：

```json
{"status":"ok"}
{"status":"ready"}
```

如果 `/readyz` 失敗，先檢查：

```powershell
docker compose ps
docker compose logs api
docker compose logs postgres
```

若 Kafka / Zookeeper stale session 造成 API 或 worker 等待，可先嘗試：

```powershell
docker compose restart zookeeper kafka api worker
```

## 2. 開啟 Dashboard

用瀏覽器開啟：

```text
http://127.0.0.1:8000/demo
```

預期畫面至少要看到：

- `Browser Agent v0.5 Dashboard`
- `Identity / RBAC`
- `Create Task`
- `Task Detail`
- `Planner / SkillHub`
- `Audit Timeline`
- `Artifacts`
- `Artifact Query`

如果頁面無法開啟，先確認 `docker compose ps` 裡 `api` service 正在 running，且 port `8000` 沒被其他程式占用。

## 3. Identity / RBAC 測試

在 `Identity / RBAC` 區塊，role 下拉選單可切換：

- `creator`
- `approver`
- `operator`
- `admin`

切換後，確認畫面會更新：

- `Actor`
- `Roles`
- `Permissions`

### Try operator create

按 `Try operator create`。

預期 `Last RBAC` 顯示：

```text
403 Forbidden: {"detail":"insufficient role"}
```

注意：這顆按鈕固定測試 **operator token 建立 task 會被拒絕**。因此，即使左側 role 下拉目前選的是 `admin`，按下 `Try operator create` 後看到 `403 insufficient role` 仍是正確結果，不代表 admin 權限壞掉。

## 4. Normal Planner Task

在 `Identity / RBAC` role 下拉選擇：

```text
creator
```

或：

```text
admin
```

在 `Create Task` 區塊選擇：

```text
Normal planner task
```

按：

```text
Create task
```

預期結果：

- `Task Detail` 顯示新的 task id。
- `Status` 先變成 `pending_approval`。
- `Policy` 顯示 allowlisted / allowed 類型原因。
- `Planner / SkillHub` 可能仍是 idle，這是正常行為，因為 Planner metadata 會在 approval 後由 worker 執行時才寫入。

## 5. Approval 測試

選取剛剛建立且狀態為 `pending_approval` 的 task。

按：

```text
Approve selected
```

Dashboard 會使用 approver token 呼叫 approval API。預期狀態流程：

```text
pending_approval -> queued -> executing -> completed
```

如果 task 長時間停在 `queued`，請檢查：

```powershell
docker compose logs worker
docker compose logs kafka
```

## 6. 結果查詢

Task 完成後，逐一檢查下列 Dashboard 區塊。

### Task Detail

預期：

- `Status` 為 `completed`。
- `Risk` 為原本 scenario 的風險等級。
- `Final URL` 指向 `https://example.com/` 或同網域 URL。
- `Score` 通常為 `100`。

### Planner / SkillHub

Normal planner task 預期：

- `Validation` 為 `pass`。
- `Fallback` 為 `not used`。
- `Planner validation errors` 為空陣列或無錯誤。

SkillHub resolved 狀態會受到是否已註冊 demo skills 影響：

- 若尚未按 `Register demo skills`，`browser.goto` / `browser.screenshot` 可能顯示 fallback 或 unresolved。
- 若已按 `Register demo skills`，再跑 `SkillHub resolved task`，預期顯示 resolved。

### Audit Timeline

預期至少看到：

- `task.created`
- `task.pending_approval`
- `task.approved`
- `task.queued`
- `task.execution_started`
- `task.artifact_written`
- `task.evaluated`
- `task.completed`

`task.approved` 的 Actor 預期是：

```text
approver@example.com
```

### Artifacts

預期至少看到：

- `screenshot`
- `html`

Screenshot preview 會由 Dashboard 用帶 token 的 fetch 載入。v0.5 的 artifact content endpoint 需要 Bearer token，因此不要用「直接開無 token artifact URL」作為通過標準。

### Artifact Query

在 `Artifact Query` 選一個 artifact，按：

```text
Check access
```

預期顯示：

```text
Access OK
```

並且 metadata JSON 會包含 content type、size、backend、redaction 等資訊。

## 7. SkillHub Resolved Task

按：

```text
Register demo skills
```

再在 `Create Task` 選擇：

```text
SkillHub resolved task
```

建立並 approve task。

預期：

- task 最後為 `completed`。
- `Planner / SkillHub` 中 `browser.goto` 顯示 resolved。
- `browser.screenshot` 顯示 resolved。
- unresolved count 為 `0` 或不再列出 goto/screenshot。

## 8. Fallback Planner Task

在 `Create Task` 選擇：

```text
Fallback planner task
```

建立並 approve task。

預期：

- task 仍可完成。
- `Planner / SkillHub` 顯示 fallback 有使用。
- `Planner validation errors` 顯示至少一筆錯誤。
- `Audit Timeline` 有 `task.plan_fallback_used`。

這個 scenario 是用來驗證 invalid Planner output 不會直接執行，而是會記錄錯誤並改用 deterministic fallback。

## 9. Blocked Domain Task

在 `Create Task` 選擇：

```text
Blocked-domain task
```

按 `Create task`。

預期：

- task 狀態為 `blocked`。
- `Policy` 顯示 domain not allowlisted 類型原因。
- `Approve selected` 不應能讓 blocked task 進入 queued。

## 10. 最小合格檢查清單

一次 V0.5 Dashboard 手動測試至少要確認：

- `/demo` 可以開啟。
- 頁面顯示 `Browser Agent v0.5 Dashboard`。
- `Identity / RBAC` 可顯示 actor、roles、permissions。
- `Try operator create` 回 `403 Forbidden: {"detail":"insufficient role"}`。
- `Normal planner task` 可以建立。
- task 建立後先進入 `pending_approval`。
- `Approve selected` 後 task 可進入 `queued`，並由 worker 完成。
- `Audit Timeline` 顯示 approval actor 為 `approver@example.com`。
- `Planner / SkillHub` 可查詢 validation 與 fallback 狀態。
- `Artifacts` 顯示 screenshot / html。
- `Artifact Query` 按 `Check access` 顯示 `Access OK`。

## 11. 測試結果記錄

手動測試完成後，請把實際結果寫入 [TEST_REPORT.md](./TEST_REPORT.md)，至少包含：

- 測試日期。
- Docker 是否啟動成功。
- `/demo` 是否可開啟。
- RBAC forbidden case 實際結果。
- Normal planner task 最終狀態。
- approval actor。
- artifact 數量與 `Check access` 結果。
- 任何限制、失敗或需要重試的地方。

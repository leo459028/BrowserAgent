# Use Cases

本文件說明目前 `BrowserAgent` scaffold 可以展示與驗證的主要使用情境。技術名詞保留必要英文，例如 `API`、`Dashboard`、`Task`、`Artifact`、`Policy`、`SkillHub`、`Planner`、`Worker`、`Playwright`。

## 1. Normal Planner Task

### 目的

驗證 allowlisted browser task 從建立、approval、worker execution、Planner metadata、artifact 保存到 evaluation 的完整流程。

### 適用對象

- 想確認 v0.4 Dashboard 是否正常的測試人員。
- 想確認 worker 與 Playwright 是否能產生 screenshot/HTML artifacts 的工程師。
- 想確認 Planner metadata 在 task 執行後是否同步寫入的人員。

### 流程

1. 在 `/demo` 選擇 `Normal planner task`。
2. 按 `Create task`。
3. Task 進入 `pending_approval`。這是目前正常行為，即使 policy decision 是 `allowed`，仍需要 human approval。
4. 按 `Approve selected`。
5. Task 進入 `queued`，worker 消費 Kafka event。
6. Worker 執行 `HeuristicPlanner`，通過 Planner schema validation。
7. Runner 解析 SkillHub capability；若尚未註冊 demo skills，會標示 `resolved=false` 並使用 builtin browser action。
8. Playwright 開啟 `https://example.com` 並擷取 screenshot。
9. 系統保存 screenshot 與 HTML artifacts。
10. Evaluator 檢查 final URL、HTML、artifacts 與 expected domain。
11. Task 完成，狀態通常為 `completed`。

### 預期結果

- `metadata.planner.valid=true`
- `metadata.planner.fallback_used=false`
- `metadata.plan` 包含 `goto` 與 `screenshot`
- `artifacts` 包含 `screenshot` 與 `html`
- evaluation verdict 為 `pass`

## 2. Fallback Planner Task

### 目的

驗證 invalid Planner output 不會直接執行，而是被記錄、fallback，並留下 audit trail。

### 流程

1. 在 `/demo` 選擇 `Fallback planner task`。
2. 建立並 approve task。
3. `HeuristicPlanner` 因 `metadata.planner_test="invalid"` 產生故意不完整的 output。
4. `validate_plan_output()` 記錄 validation error。
5. Runner 使用 deterministic fallback。
6. 若 metadata 有 `start_url`，fallback plan 是 `goto + screenshot`。
7. Runner 寫入 `task.plan_fallback_used` audit event。

### 預期結果

- `metadata.planner.valid=false`
- `metadata.planner.fallback_used=true`
- `metadata.planner.validation_errors` 至少有一筆錯誤
- `metadata.plan` 為 `goto,screenshot`
- audit timeline 有 `task.plan_fallback_used`
- task 仍可完成並產生 artifacts

## 3. SkillHub Resolved Task

### 目的

驗證 SkillHub resolver metadata 可以把 browser action 對應到已註冊 capability。

### 流程

1. 在 `/demo` 按 `Register demo skills`。
2. Dashboard 會註冊：
   - `browser.goto`
   - `browser.screenshot`
3. 選擇 `SkillHub resolved task`。
4. 建立並 approve task。
5. Runner 對每個 planner step 呼叫 `SkillHub.resolve()`。

### 預期結果

- `metadata.planner.skill_resolution.unresolved_count=0`
- `metadata.plan[].skill.resolved=true`
- `goto` 對應 `browser.goto`
- `screenshot` 對應 `browser.screenshot`
- task 仍由內建 `BrowserRunner` 執行；v0.4 不執行第三方 skill

## 4. SkillHub Missing Task

### 目的

驗證沒有對應 SkillHub skill 時，系統仍可安全執行 builtin browser action，並把 unresolved 狀態暴露給 Dashboard。

### 流程

1. 不註冊 demo skills，或清楚知道目前沒有對應 skill。
2. 建立 `SkillHub missing task`。
3. Approve task。
4. Runner 找不到 `browser.<action>` 時，寫入 fallback metadata。

### 預期結果

- `metadata.plan[].skill.resolved=false`
- `metadata.plan[].skill.entrypoint=builtin.browser.<action>`
- `metadata.planner.skill_resolution.unresolved_count` 大於 0
- task 不會因 skill missing 而被阻止

## 5. Policy 與 Approval Regression

### 目的

確認 governance gates 沒有因 Planner/SkillHub 修改而被破壞。

### Dashboard scenarios

- `Normal planner task`：allowlisted low-risk task，預期 `pending_approval`，approval 後可執行。
- `High-risk task`：預期 `pending_approval`，policy reason 是 high-risk。
- `Sensitive instruction task`：預期 `pending_approval`，policy reason 是 sensitive action。
- `Blocked-domain task`：預期 `blocked`，不可 approve。

### 自動測試覆蓋

- Domain allowlist blocking。
- High-risk approval。
- Sensitive instruction approval。
- Approval status transition。
- Failed task metadata。
- Artifact access boundary。
- Dashboard v0.4 rendering。

## 6. Artifact Governance

### 目的

驗證 artifact 不只是檔案，而是具備 metadata、audit 與 access control 的 evidence。

### Metadata

每個 artifact summary 會包含：

- `artifact_type`：`screenshot` 或 `html`。
- `content_type`：例如 `image/png` 或 `text/html; charset=utf-8`。
- `size_bytes`
- `sha256`
- `backend`：目前為 `local`。
- `retention`
- `redaction`：目前為 no-op。
- `download_url`

### Access Control

- Artifact 必須存在。
- Artifact 所屬 task tenant 必須符合 demo tenant。
- Local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 底下。
- Tenant mismatch 或 path traversal 回傳 `403`。
- Missing file 回傳 `404`。

### Dashboard

- `Artifacts` 區塊顯示 artifact table。
- Screenshot artifact 可直接 preview。
- HTML artifact 可透過 link 開啟。
- `Artifact Query` panel 顯示 metadata JSON。
- `Check access` 會呼叫 governed content endpoint。

## 7. Docker E2E Verification

### 目的

確認 Docker Compose stack 中 API、PostgreSQL、Kafka、worker、Playwright、artifact storage 可以完整串接。

### 建議流程

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

再透過 Dashboard 或 API 驗證：

- Normal planner task。
- Fallback planner task。
- SkillHub resolved task。
- Artifact content endpoint。

最新實測結果請見 [TEST_REPORT.md](./TEST_REPORT.md)。

## 目前非目標

以下項目尚未完成：

- Production operator UI。
- SSO/OIDC/RBAC。
- 真正的 MinIO/S3 artifact backend。
- 外部 LLM Planner。
- 第三方 SkillHub skill execution。
- Browser replay UI。
- Distributed tracing。
- Kubernetes deployment。
- Policy-as-code rule management。
- Per-action confirmation。

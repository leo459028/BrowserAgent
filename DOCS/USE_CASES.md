# Use Cases

本文件說明目前 `BrowserAgent` scaffold 可以展示與驗證的主要使用情境。技術名詞保留必要英文，例如 `API`、`Dashboard`、`Task`、`Artifact`、`Policy`、`SkillHub`、`Planner`、`Worker`、`Playwright`。

## 1. Auth/RBAC Smoke

### 目的

驗證 v0.5 不再使用固定 demo identity，而是依 JWT actor 與 role 控制權限。

### 流程

1. 呼叫 `/v1/auth/demo-token`，role 使用 `operator`。
2. 呼叫 `/v1/auth/me`。
3. 確認 email 是 `operator@example.com`，permission 包含 `metrics:read`。
4. 用 operator token 呼叫 `POST /v1/tasks`。

### 預期結果

- `/v1/auth/me` 回傳 actor、tenant、roles、permissions。
- operator 建立 task 回 `403`。
- `/demo` 的 `Try operator create` 顯示 forbidden。

## 2. Normal Planner Task

### 目的

驗證 allowlisted browser task 從 creator 建立、approver approval、worker execution、Planner metadata、artifact 保存到 evaluation 的完整流程。

### 流程

1. 在 `/demo` 選擇 `Normal planner task`。
2. active role 使用 `creator`，按 `Create task`。
3. Task 進入 `pending_approval`。
4. 按 `Approve selected`；Dashboard 會用 approver token 核准。
5. Task 進入 `queued`，worker 消費 Kafka event。
6. Worker 執行 `HeuristicPlanner`，通過 Planner schema validation。
7. Runner 解析 SkillHub capability；若尚未註冊 demo skills，會標示 `resolved=false` 並使用 builtin browser action。
8. Playwright 開啟 `https://example.com` 並擷取 screenshot。
9. 系統保存 screenshot 與 HTML artifacts。
10. Evaluator 檢查 final URL、HTML、artifacts 與 expected domain。

### 預期結果

- `approval.approved_by=approver@example.com`。
- audit payload 有 `actor_email=approver@example.com`。
- `metadata.planner.valid=true`。
- `metadata.planner.fallback_used=false`。
- `metadata.plan` 包含 `goto` 與 `screenshot`。
- artifacts 包含 `screenshot` 與 `html`。
- evaluation verdict 為 `pass`。

## 3. Fallback Planner Task

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

- `metadata.planner.valid=false`。
- `metadata.planner.fallback_used=true`。
- `metadata.planner.validation_errors` 至少有一筆錯誤。
- `metadata.plan` 為 `goto,screenshot`。
- audit timeline 有 `task.plan_fallback_used`。
- task 仍可完成並產生 artifacts。

## 4. SkillHub Resolved Task

### 目的

驗證 SkillHub resolver metadata 可以把 browser action 對應到已註冊 capability。

### 流程

1. 在 `/demo` 按 `Register demo skills`。
2. Dashboard 會用 admin token 註冊：
   - `browser.goto`
   - `browser.screenshot`
3. 選擇 `SkillHub resolved task`。
4. 建立並 approve task。
5. Runner 對每個 planner step 呼叫 `SkillHub.resolve()`。

### 預期結果

- `metadata.planner.skill_resolution.unresolved_count=0`。
- `metadata.plan[].skill.resolved=true`。
- task 仍由內建 `BrowserRunner` 執行；v0.5 不執行第三方 skill。

## 5. SkillHub Missing Task

### 目的

驗證沒有對應 SkillHub skill 時，系統仍可安全執行 builtin browser action，並把 unresolved 狀態暴露給 Dashboard。

### 預期結果

- `metadata.plan[].skill.resolved=false`。
- `metadata.plan[].skill.entrypoint=builtin.browser.<action>`。
- `metadata.planner.skill_resolution.unresolved_count` 大於 0。
- task 不會因 skill missing 而被阻止。

## 6. Policy 與 Approval Regression

Dashboard scenarios：

- `Normal planner task`：allowlisted low-risk task，預期 `pending_approval`，approval 後可執行。
- `High-risk task`：預期 `pending_approval`，policy reason 是 high-risk。
- `Sensitive instruction task`：預期 `pending_approval`，policy reason 是 sensitive action。
- `Blocked-domain task`：預期 `blocked`，不可 approve。

自動測試覆蓋：

- Domain allowlist blocking。
- High-risk approval。
- Sensitive instruction approval。
- Authenticated approval actor audit。
- Failed task metadata。
- Artifact access boundary。
- Dashboard v0.5 rendering。

## 7. Artifact Governance

每個 artifact summary 包含：

- `artifact_type`：`screenshot` 或 `html`。
- `content_type`。
- `size_bytes`。
- `sha256`。
- `backend`：目前為 `local`。
- `retention`。
- `redaction`：目前為 no-op。
- `download_url`。

Access control：

- Artifact 必須存在。
- Artifact 所屬 task tenant 必須符合 token tenant。
- Local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 底下。
- Tenant mismatch 或 path traversal 回 `403`。
- Missing file 回 `404`。

## 8. 目前非目標

- Production operator UI。
- 外部 SSO/OIDC/JWKS。
- 真正的 MinIO/S3 artifact backend。
- 外部 LLM Planner。
- 第三方 SkillHub skill execution。
- Browser replay UI。
- Distributed tracing。
- Kubernetes deployment。
- Policy-as-code rule management。
- Per-action confirmation。

# 使用情境

本文件說明目前 `BrowserAgent` scaffold 可以支援、展示與驗證的主要使用情境。文件中的技術名詞會保留英文，例如 `API`、`Dashboard`、`Task`、`Artifact`、`Policy`、`SkillHub`、`Planner`、`Worker`、`Playwright`，但每個情境都以繁體中文描述其目的、流程、目前能力與限制。

## 1. 受治理的瀏覽器任務執行

這個情境適合用來展示平台最核心的能力：使用者提出一個瀏覽器任務，系統先進行 `Policy` 與 approval 檢查，再由 `Worker` 執行瀏覽器動作，最後保存結果、`Artifact` 與 audit trail。

### 適用對象

- 想用 `API` 建立 browser automation task 的開發者。
- 想透過 `Dashboard` 觀察任務生命週期的操作人員。
- 想確認 allowlist、approval、audit、artifact 保存是否串起來的測試人員。

### 建立 Task 範例

```json
{
  "title": "Capture example",
  "instructions": "Open the allowlisted site and capture a screenshot.",
  "priority": 1,
  "risk_level": "low",
  "metadata": {
    "domains": ["example.com"],
    "start_url": "https://example.com",
    "expected_domain": "example.com"
  }
}
```

### 操作流程

1. 使用者透過 `API` 或 `Dashboard` 建立 `Task`。
2. `API` 驗證 request，並掃描 instructions 是否有 prompt-injection-like patterns。
3. `Policy` 檢查 domain、risk level 與 sensitive instructions。
4. 符合規則的 task 進入 `pending_approval`。
5. 操作人員 approve task 後，task 進入 `queued`。
6. `Worker` 消費 queued event，並把 task 移到 `executing`。
7. `Playwright` 開啟 allowlisted page，執行 planner 產生的 browser steps。
8. 系統擷取 screenshot 與 HTML artifacts。
9. `Evaluator` 檢查 final URL、HTML、artifacts 與 expected domain。
10. Task 最後變成 `completed`、`review` 或 `failed`。
11. 使用者可透過 `API` 或 `Dashboard` 檢視 audit、evaluation、steps 與 artifact metadata。

### 目前能力

- 支援 allowlisted domain 的基本瀏覽器任務。
- 支援 task approval gate。
- 支援 screenshot 與 HTML artifact 保存。
- 支援 task-level audit timeline。
- 支援 evaluation result 顯示。

### 目前限制

- `Planner` 目前仍是 heuristic stub，尚未接 LLM 或 `SkillHub` resolver。
- 尚未支援 production auth/RBAC。
- 尚未支援 per-action confirmation。

## 2. 本機 QA 與 Smoke Test Agent

這個情境適合用來把平台當成本機 browser smoke-test runner。它可以協助確認一個簡單 web flow 是否能被 `Worker` 開啟、截圖、保存 HTML，並透過 `Evaluator` 得到基本驗證結果。

### 適用對象

- 想快速驗證本機 Docker Compose stack 是否可用的開發者。
- 想確認 `Worker`、`Playwright`、artifact store 是否能串接成功的測試人員。
- 想把瀏覽器操作結果保存成 evidence 的 QA 使用者。

### 操作流程

1. 使用者在 `Dashboard` 選擇 normal artifact task。
2. 系統建立 task，並讓 task 進入 `pending_approval`。
3. 操作人員在 `Dashboard` approve task。
4. `Worker` 執行瀏覽器流程。
5. 系統保存 screenshot 與 HTML artifacts。
6. `Dashboard` 顯示 final URL、evaluation、artifact preview 與 artifact table。

### 目前能力

- 可開啟 allowlisted page。
- 可擷取 screenshot。
- 可擷取 HTML。
- 可驗證 final URL 與 expected domain。
- 可把 evidence 以 artifacts 形式保存。
- 可從 `Dashboard` 檢視執行結果。

### 目前限制

- 尚未支援複雜互動流程的完整規劃。
- 尚未支援 browser replay UI。
- 目前主要驗證單一 task 的端到端鏈路，不是完整 testing framework。

## 3. 人工核准關卡

這個情境展示系統如何在 `Worker` 執行前加入 human approval gate。它適合用於需要人工確認的高風險任務、敏感指令或需要留下審核紀錄的瀏覽器操作。

### 適用對象

- 需要審核 high-risk tasks 的 operator。
- 需要確認 sensitive instructions 的 reviewer。
- 需要保留 approval actor、time、note 的 audit 使用者。

### 操作流程

1. 使用者建立 task。
2. `Policy` 判斷 task 是否需要 approval。
3. Task 進入 `pending_approval`。
4. 操作人員在 `Dashboard` 或透過 `POST /v1/tasks/{task_id}/approve` approve task。
5. 系統記錄 approval row 與 audit event。
6. Task 進入 `queued`，等待 `Worker` 執行。

### 目前能力

- `risk_level=high|critical` 會要求 approval。
- 包含 `login`、`password`、`payment`、`transfer` 等 sensitive instructions 會要求 approval。
- non-allowlisted domain 會直接 `blocked`，不能 approve。
- Approval 會記錄 demo actor UUID 與 display label。

### 目前限制

- 目前沒有正式 production auth/RBAC。
- Approval actor 仍是固定 demo identity。
- 尚未支援 per-action approval 或 step-level confirmation。

## 4. Artifact 治理檢視

v0.3 的重點是讓 `Artifact` 不只是檔案，而是可以被治理、查詢、審計與安全讀取的 evidence。這個情境適合驗證 artifact metadata 是否完整、access control 是否生效，以及 `Dashboard` 是否能協助操作人員檢視 artifact。

### 適用對象

- 需要檢視 task execution evidence 的 operator。
- 需要確認 artifact metadata 與 audit 是否完整的工程師。
- 需要驗證 tenant boundary 與 base-path protection 的安全測試人員。

### 可檢視的 Artifact metadata

- `artifact_type`：例如 `screenshot` 或 `html`。
- `content_type`：例如 `image/png` 或 `text/html; charset=utf-8`。
- `size_bytes`：artifact 實際大小。
- `sha256`：artifact checksum。
- `backend`：目前為 `local`。
- `retention`：保留政策 metadata，目前為 default policy。
- `redaction`：redaction hook metadata，目前為 no-op。
- `download_url`：透過 API 存取 artifact content 的 governed access URL。

### Access control 行為

- Artifact 必須存在。
- Artifact 所屬 task tenant 必須符合目前 demo tenant。
- Local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 底下。
- Tenant mismatch 或 path traversal 會回傳 `403`。
- Missing file 會回傳 `404`。

### Dashboard 操作

- `Artifacts` 區塊會顯示 artifact table。
- Screenshot artifact 可直接 preview。
- HTML artifact 可透過 link 開啟。
- `Artifact Query` panel 會顯示 metadata JSON。
- `Check access` 會呼叫 governed content endpoint，並顯示 `Access OK` 或錯誤訊息。

### 目前限制

- `redaction hook` 目前是 no-op，只記錄 `not_applied`。
- MinIO/S3 backend 尚未實作，active backend 仍是 local filesystem。
- 尚未支援 signed URLs 或 production retention policy。

## 5. Policy Regression 測試

這個情境用來確認後續修改不會破壞既有 governance gates。當未來導入更完整的 `Planner`、`SkillHub` 或更複雜的 browser actions 時，這些 regression cases 可以幫助確認系統仍會遵守目前的 policy 行為。

### 適用對象

- 修改 `Policy` 或 `Orchestrator` 的工程師。
- 修改 `Worker` 或 `Planner` 的工程師。
- 想在 release 前確認 approval 與 blocked behavior 沒有 regression 的測試人員。

### Dashboard 可測情境

- Normal allowlisted task：預期進入 `pending_approval`，approval 後可執行。
- High-risk task：預期進入 `pending_approval`，並顯示 high-risk policy reason。
- Sensitive instruction task：預期進入 `pending_approval`，並顯示 sensitive-action policy reason。
- Blocked-domain task：預期直接進入 `blocked`，不能 approve。

### Automated tests 覆蓋

- Domain allowlist blocking。
- High-risk approval。
- Sensitive instruction approval。
- Approval status transition。
- Failed task metadata。
- Artifact access boundary。
- Dashboard v0.3 rendering。

### 目前限制

- 尚未有 CI pipeline。
- 尚未有 browser replay comparison。
- Metrics 仍是 process-local，尚未聚合 worker metrics。

## 6. SkillHub 整合前置情境

`SkillHub` 目前已經有 registration API，但尚未整合到 `Planner` 與 `Runner`。這個情境描述 v0.4 之前的準備方向：先保留版本化 capability 的資料結構，之後讓 planner output 可以選擇對應的 skill 或 tool。

### 適用對象

- 準備實作 v0.4 Planner/SkillHub integration 的工程師。
- 想定義 versioned browser capability 的平台設計者。
- 想把 tool/action selection 從 hardcoded heuristic 拆出去的維護者。

### 未來操作流程

1. 使用者或管理者透過 `POST /v1/skills` 註冊 skill。
2. `SkillHub` 保存 skill name、version、entrypoint、input/output schema、policy tags。
3. `Planner` 產生 browser plan 時，透過 `SkillHub` resolver 選擇合適 capability。
4. `Runner` validate planner output。
5. 若 planner output invalid，系統使用 deterministic fallback。
6. Task metadata 與 audit 記錄 planner version、prompt metadata 與 selected skill。

### 目前能力

- 已有 `POST /v1/skills`。
- 已有 `GET /v1/skills`。
- 已有 `SkillHub.resolve()` 的基本查詢能力。

### 目前限制

- `Planner` 尚未使用 `SkillHub`。
- Planner output JSON schema 尚未定義。
- 尚未保存 planner version 與 prompt metadata。
- 尚未有 invalid planner output fallback。

## 目前非目標

以下項目目前不屬於 v0.3 已完成範圍：

- Production operator UI。
- 完整 SSO/OIDC/RBAC。
- 真正的 MinIO/S3 artifact backend。
- Browser replay UI。
- Distributed tracing。
- Kubernetes deployment。
- Policy-as-code rule management。
- Per-action confirmation。

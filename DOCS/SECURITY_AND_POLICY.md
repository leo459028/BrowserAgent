# Security and Policy

## Auth/RBAC

v0.5 預設啟用 Bearer token 驗證。API 會驗證本機 HS256 JWT：

- signature。
- `iss = AUTH_JWT_ISSUER`。
- `aud = AUTH_JWT_AUDIENCE`。
- `exp` 尚未過期。
- 必要 claims：`sub`、`tenant_id`、`email`、`roles`。

驗證後會建立 `ActorContext`，後續 task、approval、audit、artifact access 都使用這個 actor。

## Roles

| Role | 可以做什麼 |
|---|---|
| `creator` | 建立 task、讀同 tenant task/detail/artifact |
| `approver` | 讀 task/audit/artifact、核准 `pending_approval` task |
| `operator` | 讀 task/audit/artifact/metrics |
| `admin` | 全部權限，包含 SkillHub registration |

錯誤或缺失 token 回 `401`；角色不足回 `403`。

## Production Approval

`POST /v1/tasks/{task_id}/approve` 只允許 `approver` 或 `admin`。Approval actor 只信任 token，不信任 request body 的 `approved_by`。

Audit payload 會保存：

```json
{
  "actor_user_id": "uuid",
  "actor_email": "approver@example.com",
  "actor_roles": ["approver"],
  "correlation_id": "cid"
}
```

Kafka `agent.tasks.queued` event 也會包含 authenticated actor email 與 role metadata。

## Instruction Scan

[src/browser_agent/security.py](../src/browser_agent/security.py) 會在 `POST /v1/tasks` 前檢查 prompt-injection-like instructions。

目前 block patterns：

- `ignore previous instructions`
- `reveal system prompt`
- `exfiltrate`
- `bypass`
- `steal`

命中時 API 回 `400`。

## Policy Engine

[src/browser_agent/policy.py](../src/browser_agent/policy.py) 目前是 minimal policy decision：

- non-allowlisted domain：`denied`，task 變成 `blocked`。
- `risk_level=high|critical`：`requires_approval`，task 變成 `pending_approval`。
- sensitive instruction：包含 `payment`、`transfer`、`wire`、`bank`、`password`、`mfa`、`otp`、`login` 時，task 變成 `pending_approval`。
- allowlisted low/medium task：policy decision 是 `allowed`，但本機流程仍會進入 `pending_approval`，需要 human approval 後才 queue 給 worker。

Policy reason 會寫入：

- `tasks.metadata.policy`
- audit payloads

## Artifact Access Control

Governed artifact reads：

- artifact 必須存在。
- artifact 所屬 task tenant 必須符合 token tenant。
- local artifact path 必須 resolve 在 `ARTIFACT_BASE_PATH` 底下。
- content type 來自 artifact metadata。
- content 由 `/v1/artifacts/{artifact_id}/content` inline serve。

Tenant mismatch 或 path traversal 回 `403`。

## Planner/SkillHub Security Boundary

Planner/SkillHub integration 仍是 metadata integration，不是任意 tool execution：

- Planner output 會做 schema validation。
- unsupported action 或缺少必要欄位會變成 validation error。
- invalid output 會改用 deterministic fallback。
- fallback plan 只會用 `goto + screenshot` 或 `screenshot`。
- SkillHub 找不到 skill 時會標示 `resolved=false` 並使用 builtin browser action。
- v0.5 仍不執行第三方 SkillHub skill。

## 尚未完成的安全強化

| Risk | 目前 mitigation | Planned improvement |
|---|---|---|
| 本機 JWT 不是 production IdP | HS256 + local demo claims | 外部 OIDC/JWKS |
| Policy rules hardcoded | Python policy code + audit reason | policy-as-code 與 rule version audit |
| Artifact backend 是 local storage | base-path 與 tenant checks | S3/MinIO backend 與 signed URLs |
| Browser isolation 仍是 container | Docker + Playwright | gVisor/Kata/microVM |
| Per-action confirmation 尚未實作 | task-level approval gate | action-level confirmation |

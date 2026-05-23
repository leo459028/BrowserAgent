# Security And Policy

## Auth/RBAC

V1.0 支援兩種 auth mode：

- `AUTH_MODE=local`：使用 `/v1/auth/local-token` 產生 local dev HS256 token。
- `AUTH_MODE=jwks`：使用 `AUTH_JWKS_URL` 驗證 RS256/JWKS token。

Roles：

- `creator`：建立 task、讀 task/artifact。
- `approver`：讀 task/audit/artifact、approve task。
- `operator`：讀 task/audit/artifact/metrics、readiness、DLQ operations。
- `admin`：全部權限。

## Policy

Task create 仍會檢查 allowlist domains、risk level、sensitive instruction 與 prompt-injection pattern。Non-allowlisted domain 會 blocked；需要人工審核的 task 進入 `pending_approval`。

## Artifact Access

Artifact content endpoint 必須通過 tenant check。Local backend 會檢查 path 在 `ARTIFACT_BASE_PATH` 內；S3 backend 只讀 artifact metadata 指向的 `s3://bucket/key`。

## DLQ Controls

- DLQ list、single replay、bulk replay、quarantine 只允許 operator/admin。
- Bulk replay 會跳過 quarantined tasks。
- Quarantine 會寫入 `task.dlq_quarantined` audit。

## Production Notes

- Production 不應使用預設 `APP_SECRET_KEY`。
- Production 若仍開啟 local dev token，`/v1/ops/readiness` 會回 warning。
- JWKS verifier 不等於完整 login flow；登入、session 與 IdP onboarding 仍屬後續版本。

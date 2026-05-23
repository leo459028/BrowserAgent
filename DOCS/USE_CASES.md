# Use Cases

## Use Case：Operator 檢查 Operations Readiness

1. 取得 operator local dev token。
2. 開啟 `/operations`。
3. 查看 `Operations Readiness`。
4. 預期可看到 auth mode、artifact backend、warnings、worker identity、DLQ topic。

## Use Case：Normal Browser Task

1. 在 `/operations` 選 `Normal planner task`。
2. 用 creator 建立 task。
3. Task 進入 `pending_approval`。
4. 用 approver 核准。
5. Worker 執行 Playwright browser flow。
6. Operator 查看 artifacts、audit、steps、evaluation、Replay Timeline。

## Use Case：S3 Artifact Governance

1. Docker Compose 設定 `ARTIFACT_BACKEND=s3`。
2. Task completed 後 artifacts 寫入 MinIO bucket。
3. Operations Center 顯示 artifact backend 為 `s3`。
4. Artifact content endpoint 使用 Bearer token 讀取 screenshot/html。
5. Tenant mismatch 仍回 `403`。

## Use Case：DLQ Bulk Replay

1. Operator 查 `GET /v1/dlq/tasks`。
2. 按 `Bulk DLQ replay` 或呼叫 `POST /v1/dlq/tasks/bulk-replay`。
3. Replayable tasks 回到 `queued`。
4. Quarantined tasks 出現在 skipped list。
5. Audit 寫入 `task.dlq_replayed`。

## Use Case：Quarantine Poison Task

1. Operator 對 failed DLQ task 呼叫 quarantine API。
2. `tasks.metadata.reliability.dlq.status` 變成 `quarantined`。
3. Bulk replay 不會重新排入該 task。
4. Audit 寫入 `task.dlq_quarantined`。

## Use Case：JWKS Auth Smoke

1. 設定 `AUTH_MODE=jwks`、`AUTH_JWKS_URL`、issuer、audience。
2. 用外部 IdP 或測試 JWKS 簽發 RS256 token。
3. 呼叫 `/v1/auth/me`。
4. 預期 valid token 回 actor；bad issuer/audience/expired/bad roles 回 `401`。

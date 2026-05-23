# Test Report

最後更新：2026-05-22

## V1.0 Operations Center 測試結果

日期：2026-05-22

本次完成 V1.0 MVP：Operations Center route、local dev token endpoint、optional JWKS auth、Operations Readiness、S3/MinIO artifact backend、DLQ bulk replay、DLQ quarantine、Replay-lite timeline，以及相關文件同步。

### Host 測試

Baseline 實作前：

```text
pytest -q -> 47 passed, 2 warnings in 5.18s
```

V1.0 RED tests：

```text
10 failed
```

失敗點符合預期，包含 `/operations` 尚不存在、local token endpoint 尚不存在、JWKS/S3/DLQ bulk/replay-lite 尚未實作。

V1.0 targeted tests：

```text
pytest tests/test_v10_operations_ui.py tests/test_v10_auth_jwks.py tests/test_v10_artifacts_s3.py tests/test_v10_dlq_ops.py tests/test_v10_replay.py -q
10 passed, 2 warnings in 2.30s
```

全套 host tests：

```text
pytest -q
57 passed, 2 warnings in 3.29s
```

語法檢查：

```text
python -m compileall src tests worker alembic
exit code 0
```

Diff whitespace：

```text
git diff --check
exit code 0
```

Warnings：

- `pythonjsonlogger.jsonlogger` deprecation warning。
- `.pytest_cache` 寫入 permission warning；測試通過，不影響結果。

### V1.0 Test Coverage

- `/operations` render、V1.0 title、Operations Readiness、Artifact Backend、Bulk DLQ、Replay Timeline panels。
- `/v1/auth/local-token`，舊 token route 不再是入口。
- JWKS mode 驗證 RS256 token，並拒絕 bad issuer/audience/expired/bad roles。
- `S3ArtifactStore` 寫入 governance metadata 並可讀回 bytes。
- Artifact content endpoint 支援 S3 artifact。
- DLQ bulk replay 會 replay pending tasks 並跳過 quarantined tasks。
- DLQ quarantine 寫入 metadata 與 audit。
- Replay-lite endpoint 合併 audit、steps、artifacts、evaluation。

### Docker 驗證

```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

第一次 `docker compose exec -T api pytest -q` 逾時，原因是既有 Kafka/Zookeeper stale broker session。Kafka log 顯示：

```text
KeeperErrorCode = NodeExists
```

依 runbook 執行：

```powershell
docker compose restart zookeeper kafka api worker
```

重新執行 container pytest 成功：

```text
57 passed in 2.73s
```

### Docker Operations Smoke

執行項目：

- `GET /operations`
- `POST /v1/auth/local-token` for creator / approver / operator
- `GET /v1/ops/readiness`
- creator `POST /v1/tasks`
- approver `POST /v1/tasks/{task_id}/approve`
- polling operator `GET /v1/tasks/{task_id}`
- operator `GET /v1/tasks/{task_id}/replay`
- operator `GET /v1/tasks/{task_id}/audit`
- operator `GET /v1/artifacts/{artifact_id}/content`
- operator `POST /v1/dlq/tasks/{task_id}/quarantine`
- operator `POST /v1/dlq/tasks/bulk-replay`

實際結果：

```json
{
  "operationsV10": true,
  "readinessStatus": "ready",
  "authMode": "local",
  "artifactBackend": "s3",
  "createdStatus": "pending_approval",
  "approvedStatus": "queued",
  "finalStatus": "completed",
  "artifactCount": 2,
  "firstArtifactBackend": "s3",
  "artifactStatus": 200,
  "artifactContentType": "image/png",
  "replayEvents": 14,
  "auditEvents": 9,
  "dlqCount": 0
}
```

DLQ bulk/quarantine smoke：

```json
{
  "quarantinedStatus": "quarantined",
  "replayedCount": 1,
  "skippedCount": 1,
  "skippedReason": "quarantined",
  "replayedStatus": "queued"
}
```

### 目前限制

- V1.0 有 JWKS verifier，但尚未做完整 IdP login / OIDC discovery flow。
- 尚未做 Kubernetes/Helm、secrets vault、OpenTelemetry tracing。
- Replay-lite 不含 browser session 錄影或 DOM stream。

## 2026-05-23 Architecture image archive

Change scope:
- Archived generated architecture image to `DOCS/assets/browseragent-architecture.png`.
- Added image reference/path notes to `DOCS/ARCHITECTURE.md`, `DOCS/OVERVIEW.md`, and the README technical documentation section.

Commands and results:
- `Test-Path DOCS\assets\browseragent-architecture.png` -> `True`
- `Get-Item DOCS\assets\browseragent-architecture.png | Select-Object FullName,Length` -> `Length: 1579844`
- `Test-Path (Join-Path (Resolve-Path DOCS) 'assets\browseragent-architecture.png')` -> `True`
- `git diff --check` -> passed with exit code 0

Limitations:
- No Docker verification was needed because this change only archives a static documentation image and updates Markdown references.
- One sandbox-only attempt to run a path check with `DOCS` as the command working directory failed during Windows sandbox setup; the equivalent root-workspace path check passed.

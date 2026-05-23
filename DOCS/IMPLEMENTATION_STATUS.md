# Implementation Status

最後更新：2026-05-22

## 摘要

Repository 目前已完成 **V1.0 MVP：Operations Center**。此版本提供可操作的 `/operations` 入口、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine 與 Replay-lite timeline。

## 已完成

- `GET /operations`：`Browser Agent v1.0 Operations Center`。
- `POST /v1/auth/local-token` 與 `GET /v1/auth/me`。
- `AUTH_MODE=local|jwks`，JWKS mode 支援 RS256/JWKS verifier。
- `GET /v1/ops/readiness`，限 operator/admin。
- `ARTIFACT_BACKEND=local|s3`。
- `S3ArtifactStore` 與 MinIO-compatible artifact write/read。
- `GET /v1/artifacts/{artifact_id}/content` 支援 local 與 S3。
- `POST /v1/dlq/tasks/bulk-replay`。
- `POST /v1/dlq/tasks/{task_id}/quarantine`。
- `GET /v1/tasks/{task_id}/replay`。
- TaskRunner 寫回 step status/output data。
- V1.0 tests：Operations UI、JWKS auth、S3 artifacts、DLQ ops、Replay-lite。

## 尚未完成

- 完整 IdP login / OIDC discovery flow。
- Kubernetes / Helm。
- Secrets vault。
- OpenTelemetry distributed tracing。
- Browser session 錄影或 DOM stream replay。

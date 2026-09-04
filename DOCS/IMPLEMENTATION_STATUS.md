# Implementation Status

最後更新：2026-09-04

## 摘要

Repository 目前已完成 **V1.1：Production Readiness + End-to-End Tracing + Alerting Center + Visual Replay**。此版本延續 V1.0 的 `/operations`、Operations Readiness、JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine，並新增 production-like Compose config、OIDC discovery、端到端分散式追蹤（W3C Traceparent & Span 呼叫鏈）、Production Alerting Center（7 大規則評估與非阻塞 Webhook 轉發）、以及 Visual Step Replay（步驟分頁條 + 即時截圖縮圖/DOM 預覽）。

## 已完成

- `GET /operations`：`Browser Agent v1.1 Operations Center`，整合即時 Alert Badge、Production Alerting Center、Trace Inspector 與 Visual Step Replay。
- `POST /v1/auth/local-token` 與 `GET /v1/auth/me`。
- `AUTH_MODE=local|jwks`，JWKS mode 支援 RS256/JWKS verifier 與 OIDC discovery `jwks_uri`。
- `GET /v1/ops/readiness`，限 operator/admin，包含 `production` 與 `observability` 區塊。
- `GET /v1/ops/alerts`：即時評估 7 大維運告警規則（API, DB, DLQ, Auth, Quarantine, Reliability Store, Artifact Backend）。
- `POST /v1/ops/alerts/test-dispatch`：寫入 `alert.dispatched` 審計日誌，並非阻塞轉發外部 Webhook（Slack/Discord 相容）。
- `GET /v1/ops/traces/{trace_id}`：檢索包含 HTTP Request、Kafka、Worker 與 Task Steps 的完整 Span 樹。
- `.env.production.example` 與 `docker-compose.prod.yml`。
- `X-Correlation-ID` middleware、W3C `traceparent` 解析與生成、Span 生命週期管理、OTEL-ready log schema。
- HTTP request metrics、auth failure metrics、production readiness gauge。
- `ARTIFACT_BACKEND=local|s3`，`S3ArtifactStore` 與 MinIO-compatible artifact write/read。
- `GET /v1/artifacts/{artifact_id}/content` 支援 local 與 S3。
- `POST /v1/dlq/tasks/bulk-replay` 與 `POST /v1/dlq/tasks/{task_id}/quarantine`。
- `GET /v1/tasks/{task_id}/replay`：擴充 `steps_visual`、`screenshot_url`、`trace_id`、`evaluation_summary`，向下相容保留 `timeline`。
- TaskRunner 寫回 step span、duration_ms、screenshot artifact id 與 DOM summary。
- 全套測試：74 passed（包含 tracing、alerts webhook、visual replay、operations UI、OIDC、Compose config、S3 artifacts、DLQ ops 等）。

## 尚未完成

- 完整 IdP login / callback / session flow。
- Kubernetes / Helm。
- Secrets vault。
- 外部 OTLP Collector 遠端導出。
- 完整影片串流錄影或 DOM snapshot stream。

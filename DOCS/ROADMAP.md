# Roadmap

Roadmap 以可查詢、可驗證的 implementation slice 為單位。V1.0 起，主要 UI 入口是 `/operations`。

## 已完成

- v0.1-v0.6：browser task flow、approval、audit、metrics、artifact governance、Planner/SkillHub metadata、Auth/RBAC、idempotency、rate limit、worker lock、DLQ replay。
- v1.0：Operations Center、Operations Readiness、optional JWKS auth、MinIO/S3 artifact backend、bulk DLQ replay、DLQ quarantine、Replay-lite timeline。

## V1.1 候選

- Kubernetes manifests 或 Helm chart。
- Worker autoscaling。
- Production secret management。
- OpenTelemetry distributed tracing。
- 更完整的 production alerting。
- Browser session 錄影或 DOM snapshot replay。
- 完整 OIDC discovery / login flow。

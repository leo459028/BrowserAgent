# Overview

`BrowserAgent` is an enterprise-grade platform currently at **v1.4.2: Bidirectional Remote Takeover (HITL), Cross-Browser Matrix Execution (Chromium/Firefox/WebKit), Zero-Trust Dynamic DLP, Multi-Cluster Federation & Operations Center**.

This platform integrates an API control plane, asynchronous worker fleet, cryptographic artifact and session governance, multi-tier Auth/RBAC, reliability primitives, production readiness gates, end-to-end distributed tracing, production alerting, visual step replay, scheduled task dispatching, full-motion WebM session recording, OpenTelemetry OTLP batch export, and Kubernetes/Helm deployment blueprints into an auditable operations and automation center.

---

## Release Milestones & Version Highlights

- **v0.1 – v0.6**: Established the foundational browser task lifecycle, human-in-the-loop approval gates, artifact storage governance, Planner/SkillHub metadata contracts, Auth/RBAC, idempotency keys, rate limiting, distributed worker locking, and DLQ replay.
- **v1.0**: Introduced the **Operations Center** (`/operations`), Operations Readiness audits, optional JWKS token verification, MinIO/S3 artifact backends, bulk DLQ replay, poisonous task quarantine, and Replay-Lite execution timelines.
- **v1.1**: Added Docker Compose Production Readiness validation, OIDC discovery, end-to-end distributed tracing (W3C `traceparent` context propagation and span call graphs), Production Alerting Center (7 real-time operational rules with non-blocking webhook dispatch), and Visual Step Replay (step navigation tabs with real-time DOM summaries and screenshot thumbnail previews).
- **v1.2**: Added the Scheduled Tasks dispatching engine (5-field Cron parsing, distributed Redis lease locks, anti-reentrancy policies), Session Vault (Playwright `storage_state` browser credential governance, automated cross-task injection, one-click revocation), full-motion WebM video recording and playback, OpenTelemetry OTLP batch export (background asynchronous span streaming to APMs), and production Kubernetes manifests (`deploy/k8s/`) with KEDA Kafka autoscaling blueprints.
- **v1.3**: Added Enterprise OIDC Authorization Code Flow (PKCE, state validation, HttpOnly `ba_session` cookies, frontend SSO login), Session Vault KMS envelope encryption (Local, AWS KMS, and HashiCorp Vault drivers with AES-256-GCM and tenant isolation), Heuristic DOM Selector Self-Healing (semantic, text, and structural similarity fallback cascade), multi-priority weighted queues (`agent.tasks.high`, `agent.tasks.queued`, `agent.tasks.batch`), live browser WebSocket frame broadcasting (`WS /v1/tasks/{id}/live-stream`), online task abortion (`POST /v1/tasks/{id}/abort`), and Enterprise Helm 3 Chart packages with ArgoCD GitOps blueprints.
- **v1.4**: Introduced Bidirectional Remote Takeover & HITL (reverse control channel, execution pausing, remote mouse/keyboard injection, human intervention audit tracking), Cross-Browser Matrix Execution Engine (Chromium, Firefox, and WebKit multi-engine dispatch and aggregated comparison), Zero-Trust Dynamic DLP (CSS blur masking on password fields, Bearer token/API key regex redaction, recursive metadata scrubbing), Multi-Cluster Federation & Failover (distributed heartbeat leases, leader election, split-brain protection, `/v1/ops/federation/re-election`), and Operations Center v1.4 UI enhancements.
- **v1.4.2 (Current)**: Open Source release and internationalization. Completed open-source governance compliance (Apache-2.0 License, Contributing Guidelines, Code of Conduct, Security Vulnerability Disclosure Policy, GitHub Issue & PR templates), hardened `.env.example`, English documentation suite, and alignment with OpenAI Codex for Open Source requirements.

---

## Documentation Index

| Document | Description |
| :--- | :--- |
| **[README.md](../README.md)** | Project introduction, AI Agent Safety pillars, architecture overview, and quick-start guide. |
| **[API.md](./API.md)** | Comprehensive API documentation for Auth, Tasks, Matrix, HITL Takeover, DLP, Federation, Scheduled Tasks, Session Vault, Video, Alerting, and Readiness endpoints. |
| **[ARCHITECTURE.md](./ARCHITECTURE.md)** | Deep architectural analysis covering Control Plane, Data Plane, Governance Layer, HITL reverse control channel, and multi-engine worker fleets. |
| **[CONFIGURATION.md](./CONFIGURATION.md)** | Environment variables reference, Docker Compose configurations, Kubernetes manifests, Helm values, and secrets management. |
| **[DATA_MODEL.md](./DATA_MODEL.md)** | SQLAlchemy database models, table schemas, migration scripts, and metadata specifications. |
| **[SECURITY_AND_POLICY.md](./SECURITY_AND_POLICY.md)** | Security threat modeling, RBAC permission matrix, Zero-Trust DLP masking, KMS envelope encryption, and network egress boundaries. |
| **[RUNBOOK.md](./RUNBOOK.md)** | SRE operations procedures, cluster failover guides, HITL intervention workflows, and disaster recovery. |
| **[USE_CASES.md](./USE_CASES.md)** | Enterprise case studies: CAPTCHA human takeover, cross-browser rendering matrices, credential protection, and multi-region disaster recovery. |
| **[OBSERVABILITY.md](./OBSERVABILITY.md)** | OpenTelemetry tracing, Prometheus metrics, structured JSON logging, alerting rules, and telemetry visualization. |
| **[IMPLEMENTATION_STATUS.md](./IMPLEMENTATION_STATUS.md)** | Feature tracking matrix, completed deliverables, and v1.5 candidate evolutions. |
| **[ROADMAP.md](./ROADMAP.md)** | Historical milestone evolution and future platform roadmap. |
| **[DEVELOPMENT.md](./DEVELOPMENT.md)** | Local development environment setup, mock backends, and test suite execution. |
| **[manual_test.md](./manual_test.md)** | End-to-end Operations Center manual test guide, checklist, and verification scripts. |
| **[TEST_REPORT.md](./TEST_REPORT.md)** | Verified test execution reports (105 tests across 20 modules), real-browser runs, and Docker benchmarks. |

---

## Current Operational Boundaries & Notes

- **Enterprise Cloud Ingress & KMS**: While complete Kubernetes Kustomize manifests, Helm 3 charts, and ArgoCD blueprints are provided, enterprise cloud production deployments (AWS EKS, GCP GKE, Azure AKS) require pairing with organization-specific Ingress Controllers, TLS certificates, and production cloud KMS keys.
- **Deterministic Heuristics**: The selector self-healing engine uses deterministic DOM attribute similarity algorithms rather than asynchronous external vision LLMs, guaranteeing low-latency recovery, predictable behavior, and zero risk of external prompt injection.
- **HITL Takeover Channel**: The bidirectional reverse control channel supports click, text input, and key press injection. Advanced gestures (such as multi-point touch or drag-and-drop) are scheduled for subsequent iterations.
- **Multi-Cluster Federation**: Cluster leases and heartbeats rely on Redis distributed key expiration. For high-latency cross-region links, lease TTLs should be adjusted accordingly (default: 30s).
- **Cross-Browser Engine Binaries**: Ensure worker host environments or container images have all browser engines installed (`playwright install --with-deps chromium firefox webkit`).

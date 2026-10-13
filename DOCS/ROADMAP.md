# Platform Roadmap & Milestone Evolution

The BrowserAgent roadmap evolves through verifiable, observable, and fully auditable architectural slices. Starting from v1.0, the primary operational console is hosted at `/operations`.

---

## Completed Milestones

### v0.1 – v0.6: Foundations of Governed Browser Automation
- Established asynchronous task lifecycle: `pending_approval` ➜ `queued` ➜ `running` ➜ `completed` / `failed`.
- Implemented human-in-the-loop approval gates for high-risk browser workflows.
- Introduced token bucket rate limiting, idempotency key deduplication, and distributed worker task locking.
- Created immutable append-only audit logging and Dead Letter Queue (DLQ) task recovery.
- Established Planner and SkillHub schema contracts.

### v1.0: Operations Center & Enterprise Artifact Governance
- Launched the unified **Browser Agent Operations Center** web console (`/operations`).
- Added Operations Readiness diagnostics verifying DB, Kafka, S3, and worker status.
- Introduced S3/MinIO artifact storage backend with SHA-256 integrity hashing and tenant path containment.
- Implemented bulk DLQ replay and poisonous task quarantine isolation.
- Built backward-compatible Replay-Lite execution timelines.

### v1.1: Distributed Observability & Visual Step Replay
- End-to-end distributed tracing: W3C `traceparent` propagation, span lifecycle management, and circular in-memory TraceBuffer.
- Production Alerting Center: Real-time evaluation of 7 operational reliability rules with non-blocking webhook dispatching (Slack/Discord).
- Visual Step Replay: Step navigation tabs featuring DOM summaries, execution durations, and screenshot thumbnails.
- Docker Compose Production Readiness hardening validation and OIDC discovery.

### v1.2: Scheduled Tasks, Session Vault & Full Video Replay
- Scheduled Tasks Engine: Standard 5-field Cron evaluation, distributed Redis leasing locks, and anti-reentrancy concurrency policies (`skip`/`allow`).
- Session Vault: Playwright `storage_state` browser credential governance, automated cross-task injection, and one-click revocation.
- Full Video Recording: Continuous WebM screen video recording persisted to ArtifactStore with an embedded HTML5 player.
- OpenTelemetry OTLP Exporter: Asynchronous background Batch Span Exporter streaming traces to external APMs (Jaeger, Tempo, Datadog).
- Kubernetes Production Manifests: Complete Kustomize package (`deploy/k8s/`) and KEDA autoscaling blueprints.

### v1.3: Enterprise KMS Vault, Self-Healing & Live Telemetry
- Enterprise OIDC Authorization Code Flow SSO: PKCE verification, CSRF state protection, and secure HttpOnly `ba_session` cookies.
- Cryptographic KMS Envelope Encryption: AES-256-GCM envelope encryption supporting Local Keystore, AWS KMS, and HashiCorp Vault with tenant AAD binding.
- Heuristic Selector Self-Healing Cascade: 3-tier fallback recovery (semantic attributes, visible text similarity, DOM hierarchy) with `task.self_healed` auditing.
- Multi-Priority Queues: Dedicated traffic routing across `agent.tasks.high`, `queued`, and `batch` with worker pool isolation.
- Live Telemetry Broadcasting: Low-latency JPEG frame streaming over WebSockets (2 FPS) and online task cancellation (`POST /v1/tasks/{id}/abort`).
- Enterprise Helm 3 Chart (`deploy/helm/browser-agent/`) and GitOps ArgoCD continuous delivery blueprints.

### v1.4: Human-in-the-Loop Takeover, Multi-Engine Matrix & Zero-Trust DLP
- Bidirectional Remote Takeover (HITL): Execution pausing, reverse control channel for remote mouse clicks and keyboard typing, and human intervention audit accounting.
- Cross-Browser Matrix Execution Engine: Concurrent multi-engine dispatch across Chromium, Firefox, and WebKit with automated side-by-side comparison of execution times, verdicts, DOM self-healing, and rendering screenshots.
- Zero-Trust Dynamic DLP: Dynamic CSS Gaussian blur masking on sensitive DOM nodes, recursive regex scrubbing of Bearer tokens and API keys, and secret sanitization across all artifacts and metadata.
- Multi-Cluster Scheduling Federation: Distributed heartbeat leases, automatic leader re-election, split-brain protection, and forced failover re-election endpoints.

### v1.4.2 (Current): Open Source & Internationalization Release
- Complete Open Source compliance: Standard Apache-2.0 License, Contributing Guidelines, Contributor Covenant Code of Conduct, Security Vulnerability Policy, GitHub Issue & PR Templates.
- Hardened `.env.example` with comprehensive documentation and secure defaults.
- Complete English documentation suite aligned with OpenAI Codex for Open Source standards.

---

## Future Candidate Roadmap (v1.5+)

- **Interactive Remote Desktop WebRTC Console**: Transition from JPEG WebSocket frame streaming to ultra-low-latency bidirectional WebRTC media streams with multi-cursor collaborative drag-and-drop.
- **Adaptive Jittered Backoff & Circuit Breaker**: Dynamic traffic-aware retry policies with automatic circuit breaking for degraded downstream websites.
- **Locally Deployed Small VLM Agent Assistance**: Optional integration of local open-weights vision language models (e.g., Llama-Vision-11B or Qwen2-VL) executed strictly on-premises for complex spatial visual reasoning.
- **Zero-Trust Device Fingerprinting**: Hardware security token authentication and dynamic context-aware policy enforcement for high-risk browser sessions.

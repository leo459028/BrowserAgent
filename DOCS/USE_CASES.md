# Enterprise Use Cases & Operational Patterns

This document details verified operational patterns and enterprise use cases for BrowserAgent across compliance, infrastructure engineering, security, and agent safety operations.

---

## 1. Operations Readiness Diagnostics
- **Context**: Operator performs shift handoff or cluster maintenance verification.
- **Workflow**:
  1. Operator acquires local developer token or authenticates via OIDC SSO.
  2. Navigates to `/operations` and inspects the **Operations Readiness** diagnostic panel.
  3. Validates database connectivity, message bus partition health, S3/MinIO bucket access, worker pool heartbeats, and DLQ topic status.

---

## 2. Hardened Production Readiness Audit
- **Context**: SRE team audits containerized deployment configurations prior to production promotion.
- **Workflow**:
  1. Renders production-like compose configuration via `docker compose --env-file .env.production.example -f docker-compose.prod.yml config`.
  2. Issues `GET /v1/ops/readiness` with valid bearer credentials.
  3. Verifies `production.status` returns `ready`, confirming disabled local tokens, active RS256 JWKS/OIDC auth, Redis reliability store, Kafka bus, and S3 artifact backend.

---

## 3. Governed Task Lifecycle with Human Approval & Visual Replay
- **Context**: Business operations executes a regulated data retrieval task requiring compliance proof.
- **Workflow**:
  1. Operator selects `Normal planner task` in the Operations Center and submits the task.
  2. Because the task touches sensitive domains, the policy engine gates it into `pending_approval`.
  3. Approver reviews the proposed action plan in the **Task Detail** view.
  4. The **`Approve selected`** button toggles from grey to bright green; the approver clicks to authorize execution.
  5. The task routes to the Kafka queue and completes execution on an assigned Playwright worker.
  6. Operator inspects **Visual Step Replay**, browsing step tabs to review execution durations (ms), DOM summaries, and screenshot thumbnails.

---

## 4. S3 Cryptographic Artifact Governance
- **Context**: Organization requires centralized, immutable compliance storage for audit evidence.
- **Workflow**:
  1. Tasks persist screenshots, HTML snapshots, WebM recordings, and storage states to S3/MinIO buckets with SHA-256 integrity checksums.
  2. Users retrieve artifacts via `GET /v1/artifacts/{id}/content`.
  3. The storage layer verifies tenant ownership and enforces path traversal guards, returning HTTP 403 on tenant mismatches.

---

## 5. Dead Letter Queue (DLQ) Bulk Replay & Poison Quarantine
- **Context**: Downstream network interruption causes transient task failures.
- **Workflow**:
  1. Operator inspects failed tasks via `GET /v1/dlq/tasks`.
  2. Initiates bulk recovery by clicking **`Bulk DLQ Replay`** or calling `POST /v1/dlq/tasks/bulk-replay`.
  3. For tasks failing due to permanent fatal conditions (poison payloads), the operator triggers `POST /v1/dlq/tasks/{id}/quarantine`.
  4. Quarantined tasks are excluded from bulk replay flows and logged with `task.dlq_quarantined` audit entries.

---

## 6. Production Alerting & Webhook Notifications
- **Context**: Continuous reliability monitoring across background worker fleets.
- **Workflow**:
  1. The AlertEvaluator continuously monitors 7 operational reliability rules (DLQ backlog, failure rates, worker liveness, DB latencies).
  2. When thresholds breach, the alerting center dispatches non-blocking asynchronous notifications to configured Slack/Discord webhooks with a 3-second timeout.
  3. Administrators execute `POST /v1/ops/alerts/test-dispatch` to verify webhook routing and channel delivery.

---

## 7. Distributed Trace Inspection with W3C Propagation
- **Context**: SRE diagnoses step latency anomalies across microservices.
- **Workflow**:
  1. Operator copies the `Trace ID` from a task record and enters it into the **Trace Inspector**.
  2. Queries `GET /v1/ops/traces/{trace_id}`, combining API HTTP spans, Kafka dispatch spans, and Playwright execution spans into a hierarchical tree view.
  3. Pinpoints exact bottleneck steps (e.g., slow DOM locators or network wait conditions).

---

## 8. Scheduled Tasks Engine for Recurring Smoke Tests
- **Context**: Routine inspection of SaaS dashboards and partner portals every morning.
- **Workflow**:
  1. Operator creates a schedule under **Scheduled Tasks** with a 5-field Cron expression (e.g., `0 9 * * *`).
  2. The background scheduler acquires distributed Redis lease locks (`scheduler:lock`, TTL 55s) and dispatches tasks at designated times.
  3. If configured with `concurrency_policy: skip`, overlapping runs are skipped if the previous instance is still executing.
  4. Operators can click **`Run Now`** at any time to trigger an immediate manual inspection run.

---

## 9. Session Vault KMS Envelope Encryption & Credential Governance
- **Context**: Secure reuse of authenticated browser sessions without storing cleartext passwords or cookies.
- **Workflow**:
  1. Upon successful login, Playwright serializes cookies and local storage tokens into an encrypted `storage_state`.
  2. Envelope encryption encrypts the payload using AES-256-GCM with a transient DEK, protected by KMS (Local, AWS KMS, or HashiCorp Vault) and bound to `tenant_id` via AAD.
  3. Subsequent inspection tasks automatically reuse the session, avoiding repetitive 2FA challenges.
  4. Operators run `GET /v1/sessions/{name}/validate` to verify KMS integrity, or click **`Revoke`** (`DELETE /v1/sessions/{name}`) to immediately invalidate compromised credentials.

---

## 10. Full-Motion WebM Video Recording & Playback
- **Context**: Auditing complex multi-step browser workflows for regulatory compliance.
- **Workflow**:
  1. Tasks execute with `record_video=True`.
  2. Playwright captures full-resolution browser window screen recordings, compressing them into WebM format upon context teardown.
  3. Video files are persisted to ArtifactStore and streamed via `/v1/tasks/{id}/video` directly to the Operations Center embedded HTML5 player.

---

## 11. OpenTelemetry OTLP Streaming to External APMs
- **Context**: Enterprise-wide observability integration into centralized monitoring stacks (Jaeger, Datadog).
- **Workflow**:
  1. Administrator configures `OTEL_EXPORTER_OTLP_ENDPOINT`.
  2. The background `OtlpBatchSpanExporter` collects spans asynchronously and pushes standard OTLP JSON payloads in batches.
  3. Built-in queue overflow protection safely drops spans if external APM endpoints experience downtime, shielding core automation workflows.

---

## 12. Kubernetes & KEDA Autoscaling Worker Fleet
- **Context**: Handling fluctuating task volumes with cost-effective cloud resource scaling.
- **Workflow**:
  1. Deployed to Kubernetes using `deploy/k8s/` or Helm charts (`deploy/helm/browser-agent/`).
  2. KEDA `ScaledObject` monitors Kafka consumer lag on `agent.tasks.queued`.
  3. As scheduled tasks trigger concurrent runs, KEDA automatically scales worker pods from 1 to 10 replicas, scaling back down once queues drain.

---

## 13. Enterprise OIDC SSO Authorization Code Flow
- **Context**: Single Sign-On (SSO) login with enterprise identity providers (Keycloak, Okta, Azure AD).
- **Workflow**:
  1. Operator clicks **`SSO Login (OIDC)`** on `/operations`.
  2. The browser initiates PKCE Authorization Code Flow, redirecting to the enterprise IdP with a SHA-256 code challenge and random CSRF state.
  3. Upon successful login, the callback exchanges codes for tokens and sets an HttpOnly, SameSite=Strict `ba_session` cookie.

---

## 14. Priority Queues & Worker Pool Partitioning
- **Context**: Isolating mission-critical incident responses from high-volume batch jobs.
- **Workflow**:
  1. High-priority incident tasks are submitted with `priority: 5`.
  2. The orchestrator routes the task to `agent.tasks.high`.
  3. Dedicated high-priority worker pools consume and execute the task immediately, bypassing queued batch tasks in `agent.tasks.batch`.

---

## 15. Real-Time Telemetry Broadcasting & Online Abort
- **Context**: Operator observes misbehaving or looping automation tasks.
- **Workflow**:
  1. Operator opens the live stream canvas (`WS /v1/tasks/{id}/live-stream`) streaming frames at 2 FPS.
  2. If the agent enters an unexpected page or loop, operator clicks **`Abort Task`** (`POST /v1/tasks/{id}/abort`).
  3. Worker intercepts the abort flag before the next step, safely closing Playwright contexts and marking the task `aborted`.

---

## 16. Deterministic Selector Self-Healing Cascade
- **Context**: Target website deploys an unexpected frontend UI update, altering element IDs or classes.
- **Workflow**:
  1. A step fails to locate `button#login-old`.
  2. The `HeuristicSelfHealingEngine` evaluates semantic attributes (`data-testid`, `aria-label`), visible text similarity, and DOM hierarchy.
  3. If similarity exceeds `0.6`, the engine recovers the selector and completes the step.
  4. The recovery event is logged as `task.self_healed` and highlighted with a green `Self-Healed ✓` badge in the Operations Center.

---

## 17. Bidirectional Remote Takeover (HITL) for CAPTCHA Resolution
- **Context**: Autonomous agent encounters an interactive Cloudflare Turnstile, hCaptcha, or SMS OTP verification wall.
- **Workflow**:
  1. Operator notices the challenge in the live stream and clicks **`Pause (Takeover)`** (`POST /v1/tasks/{id}/pause`).
  2. The worker halts autonomous execution and enters an interactive poll-wait loop.
  3. Operator clicks the challenge checkbox directly on the canvas (`action: click`) or enters an SMS verification code into `Remote Key Input` (`action: type`).
  4. After resolving the barrier, operator clicks **`Resume Task`** (`POST /v1/tasks/{id}/resume`).
  5. Automation resumes smoothly, with the intervention duration audited under `task.human_intervened = True`.

---

## 18. Cross-Browser Matrix Execution & Layout Verification
- **Context**: QA engineers verifying checkout flow compatibility across different rendering engines.
- **Workflow**:
  1. Engineer clicks **`Dispatch Matrix (3 Engines)`** (`POST /v1/tasks/matrix`).
  2. The system generates three linked tasks sharing a `matrix_id`, dispatched across Chromium, Firefox, and WebKit.
  3. Workers execute the instructions concurrently on distinct browser engines.
  4. Engineer reviews the **Cross-Browser Matrix Comparison** panel, comparing rendering discrepancies, execution times, and verdicts.

---

## 19. Zero-Trust Dynamic DLP (Data Loss Prevention)
- **Context**: Tasks handling credentials or sensitive tokens must prevent cleartext leakage into screenshots, videos, or external APM spans.
- **Workflow**:
  1. Zero-Trust DLP injects CSS Gaussian blur (`filter: blur(8px)`) into `input[type="password"]` and configured secret selectors.
  2. Live stream frames, WebM recordings, and screenshots capture blurred pixels at the source.
  3. Regex filters scrub Bearer tokens, OpenAI API keys (`sk-...`), and AWS keys from metadata, replacing them with sanitized placeholders.

---

## 20. Multi-Cluster Scheduling Federation Disaster Recovery
- **Context**: High-availability scheduling across multi-region clusters (e.g., Tokyo Primary and Osaka Standby).
- **Workflow**:
  1. The Tokyo leader node periodically renews its distributed Redis lease (every 5s, TTL 15s).
  2. If the Tokyo cluster experiences network isolation, its heartbeat renewal ceases.
  3. The Osaka standby node detects lease expiration and automatically promotes itself to Leader, assuming scheduling responsibilities without human intervention.
  4. SREs can manually trigger leadership migrations via **`Force Re-election`** for maintenance drills.

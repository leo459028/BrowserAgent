# Development & Testing Guide

This guide details local environment setup, testing procedures, module test catalogs, and bootstrapping workflows for contributors.

---

## Local Verification Commands

Run the primary automated quality gates:

```bash
# 1. Run all unit and integration tests
pytest -q

# 2. Verify clean Python bytecode compilation across all modules
python -m compileall src tests worker alembic

# 3. Check for trailing whitespace or formatting conflicts
git diff --check
```

---

## Test Suite Catalog (20 Modules, 105 Tests Passing)

The project includes 20 comprehensive test modules covering edge cases, failure injection, security boundaries, and real browser runs:

| Test Module | Coverage & Verification Scope |
| :--- | :--- |
| `tests/test_v01_operations.py` | Operations Center template rendering, artifact serialization, task listings, and audit timelines. |
| `tests/test_v04_skillhub.py` | SkillHub registry metadata, step resolution, and skill version validation. |
| `tests/test_v05_auth_rbac.py` | Local development token issuance, role gates (`creator`, `approver`, `operator`, `admin`), and tenant artifact containment. |
| `tests/test_v06_reliability.py` | Idempotency keys, token bucket rate limiting, reliability backends, worker locks, and DLQ replay mechanics. |
| `tests/test_v10_operations_ui.py` | Base Operations Center UI interactions and state displays. |
| `tests/test_v10_auth_jwks.py` | RS256 JWKS verification logic, public key decoding, and token expiry validation. |
| `tests/test_v10_artifacts_s3.py` | S3/MinIO artifact storage backend, bucket initialization, and binary content retrieval. |
| `tests/test_v10_dlq_ops.py` | Dead Letter Queue single replay, bulk replay, and poisonous task quarantine isolation. |
| `tests/test_v10_replay.py` | Replay-Lite normalized event timelines combining audits, steps, and artifacts. |
| `tests/test_v11_tracing.py` | W3C `traceparent` parsing, Span lifecycle management, in-memory circular TraceBuffer, and trace inspector endpoints. |
| `tests/test_v11_alerts_webhook.py` | 7 real-time operational reliability rules, non-blocking asynchronous webhook forwarding, and admin test dispatch. |
| `tests/test_v11_visual_replay.py` | Visual Step Replay data structures, DOM summaries, thumbnail linkages, and span correlation. |
| `tests/test_v11_operations_ui.py` | Operations Center UI rendering: Alert Badge, Alerting Center, Trace Inspector, and Visual Step Replay tabs. |
| `tests/test_v12_scheduler.py` | 5-field Cron evaluation, distributed Redis leasing locks, anti-reentrancy concurrency policies (`skip`/`allow`), and automated task dispatching. |
| `tests/test_v12_session_vault.py` | Playwright `storage_state` serialization, multi-tenant credential isolation, automated session injection, and revocation. |
| `tests/test_v12_video_artifact.py` | Full-motion WebM browser screen video recording, artifact persistence, and video streaming endpoints. |
| `tests/test_v12_otlp_exporter.py` | Background asynchronous Batch Span Exporter, queue overflow protection, payload formatting, and metrics. |
| `tests/test_v12_apis.py` | Scheduled Tasks CRUD/Trigger, Session Vault query/revoke, Video streaming, and Kubernetes/OTLP readiness checks. |
| `tests/test_v13_features.py` | KMS envelope encryption (Local/AWS/Vault), AES-256-GCM tenant AAD isolation, master key rotation, heuristic selector self-healing cascade, multi-priority queue routing (`high`/`queued`/`batch`), WebSocket live streaming, online task abort, and OIDC PKCE Code Flow SSO. |
| `tests/test_v14_features.py` | Cross-browser matrix dispatch (`chromium`, `firefox`, `webkit`), bidirectional remote takeover (HITL pause, click/type injection, resume, audit tracking), Zero-Trust Dynamic DLP blur masking and token redaction, multi-cluster scheduling federation heartbeats, leader election, failover, and v1.4 API RBAC gates. |
| `tests/test_v14_playwright_e2e.py` | Real headless Chromium browser end-to-end verification of `/operations` page rendering, v1.4 badges, engine selection, HITL interaction controls, and screenshot artifact generation (`tests/artifacts/v14_operations_playwright_test.png`). |

---

## Docker Integration Testing

When validating containerized integration flows:

```bash
# Build and spin up containers
docker compose up -d --build

# Run test suite inside API container
docker compose exec -T api pytest -q
```

Docker Compose spins up:
- **PostgreSQL**: System of record for tasks, schedules, and audit trails.
- **Redis**: Reliability backend, rate limiting, and distributed leasing locks.
- **Kafka**: Multi-priority event streaming bus (`high`, `queued`, `batch`, `dlq`).
- **MinIO**: S3-compatible object storage backend.
- **API**: FastAPI Control plane and Operations Center at `http://localhost:8000/operations`.
- **Worker**: Asynchronous Kafka consumer and Playwright runner fleet.

---

## Bootstrap Script (`scripts/bootstrap.py`)

The bootstrap script performs essential initialization:
1. Executes database schema migrations via SQLAlchemy/Alembic.
2. Seeds default development tenant and user credentials (`ops@example.com`, etc.).
3. Verifies or creates the MinIO/S3 artifact bucket (`browser-agent`).
4. Pre-creates Kafka topics when `BOOTSTRAP_KAFKA_TOPICS=true`.

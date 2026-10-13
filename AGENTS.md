# BrowserAgent Project Engineering Guidelines (AGENTS.md)

This file defines mandatory working guidelines for future AI agents and software engineers working in this repository. Follow the specifications in this file first before referencing `README.md` and `DOCS/OVERVIEW.md`.

---

## Scope & Applicability

These guidelines apply across the entire BrowserAgent repository. Unless a subdirectory provides a more specific `AGENTS.md`, all code contributions, testing workflows, and documentation updates must strictly comply with this document.

---

## 1. Planning Requirements

Any proposal for a new version, feature, or bug fix must include a verifiable UI or Dashboard entrypoint for inspection and testing. Since v1.0, the default primary operations console is `/operations` (Operations Center; `/demo` is preserved for backward compatibility). If `/operations` is unsuitable for a specific scenario, the plan must clearly explain the alternative interface (e.g., API smoke tests, a dedicated dashboard panel, or other queryable/verifiable endpoints).

Each plan must explicitly cover:
- **Feature Objectives & Success Criteria**.
- **UI / Dashboard Verification Steps**: How operators will interact with, query, and validate the feature.
- **Data Flow & State Transitions**: Changes to APIs, request/response schemas, task metadata, or state machines.
- **Implementation Architecture**: Affected components, service layers, and modules.
- **Testing Plan**: Specific automated commands, integration tests, and manual verification steps.
- **Documentation Updates**: Required documentation revisions (must include `DOCS/manual_test.md` and code-to-doc parity checks).
- **Test Reporting**: Real test metrics and outputs to be recorded in `DOCS/TEST_REPORT.md`.

Do not merely specify high-level concepts or anticipated outcomes; write concrete, actionable plans that any subsequent engineer can execute immediately.

---

## 2. Implementation Standards

Implementations should prioritize and build upon the established architectural foundation of the project:
- **API Control Plane**: FastAPI.
- **Relational Data Model**: SQLAlchemy with Alembic migrations.
- **Web Console / Operations Center**: Existing `/operations` Jinja2 templates and vanilla JavaScript.
- **Background Tasks & Event Bus**: Asynchronous worker fleet consuming Apache Kafka topics.
- **Browser Automation**: Playwright multi-engine runner (Chromium, Firefox, WebKit).
- **Testing**: pytest.

Avoid introducing unnecessary database tables, schema migrations, external cloud dependencies, or excessive architectural abstractions. If a requirement genuinely necessitates database schema modifications, the plan must clearly document the rationale, data compatibility, migration/rollback scripts, verification methods, and documentation sync scope. When extending existing features, prefer reusing current data flows; evolve models incrementally as needed across major versions.

Before modifying code, thoroughly inspect relevant files and existing test cases. Preserve all unrelated user modifications in the working tree; restrict edits to the scope required by the active task.

---

## 3. Testing & Quality Assurance

Comprehensive testing must be performed upon completing code modifications. If Docker is required, remind the user to start Docker Desktop before running containerized verification.

### Core Quality Gate Commands:
```powershell
pytest -q
python -m compileall src tests worker alembic
git diff --check
```

### Containerized Verification (When Docker is available):
```powershell
docker compose up -d --build
docker compose exec -T api pytest -q
```

### Operations Center & Task Lifecycle Verification:
If changes impact the Operations Center or the browser task lifecycle, verify that:
- `/operations` renders cleanly without console or network errors.
- New automation tasks can be created from the UI.
- Tasks requiring review correctly enter `pending_approval`, and the `Approve selected` button dynamically activates (toggles from disabled grey to active bright green) when selected.
- Approved tasks are consumed by workers from Kafka priority queues and execute to completion.
- Visual Step Replay (step tabs, execution durations, DOM summaries, screenshot previews) and the WebM Video Player function properly.
- Scheduled Tasks (Cron parsing, distributed Redis lease locking, `Run Now` immediate triggers, pause/resume) operate as expected.
- Session Vault (storage state retrieval, cross-task credential injection, one-click revocation) remains cryptographically secure.
- Production Alerting Center (7 operational reliability rules, webhook test dispatching) and Trace Inspector (hierarchical span trees) are operational.
- Planner / SkillHub / artifacts / audit logs / metrics / DLQ endpoints function properly.
- Existing scenarios (Normal, Fallback, SkillHub resolved, SkillHub missing, Self-Healing) continue to pass.

All verified test outputs must be recorded in `DOCS/TEST_REPORT.md`, including execution date, commands run, test pass counts, Operations Center validation results, Docker benchmarks, and known limitations. Never record hypothetical or unverified results.

### Manual UI Testing Guide & `manual_test.md` Synchronization
Whenever a new version or significant capability is delivered, you must provide the user with a detailed manual testing walkthrough and synchronize `DOCS/manual_test.md`:
1. **Walkthrough Requirements**:
   - Environment initialization (Docker Compose startup, ingress URLs).
   - Top status badges guide (Alert Badge, K8s Badge, OTLP Badge, DLP Badge, Federation Badge, etc.).
   - Step-by-step UI verification flow (Creation, Approval, Execution, Step Replay, Video Playback, Schedules, Session Vault, Traces, Alerts, DLQ, RBAC).
   - UI FAQs (e.g., safety guardrail button disabling, video loading triggers).
   - Minimum acceptance checklist.
   - One-click automated smoke test script (PowerShell / curl).
2. **`DOCS/manual_test.md` Updates**:
   - Keep `DOCS/manual_test.md` fully updated and increment the version header (e.g., v1.4.2).
   - Ensure all UI button labels, payload keys, and route paths match current code exactly.

---

## 4. Documentation Parity Requirements (Mandatory for Every Iteration)

After tests pass, perform an exhaustive audit to ensure 100% synchronization between codebase and documentation:

### Code-to-Documentation Audit Checklist:
- **API Routes & HTTP Verbs**: Endpoint paths (e.g., `/v1/scheduled-tasks`, `/v1/sessions`), HTTP methods (GET, POST, PATCH, DELETE), and status codes.
- **Request Payloads & Response Schemas**: Key names (e.g., `task_template`, `is_active`), data types, and structural formats.
- **Database Schemas**: SQLAlchemy models and Alembic migration scripts.
- **Metadata Contracts**: Task metadata, Session Artifact metadata, Video metadata, and reliability fields.
- **UI Elements & Button Labels**: Exact button text in the Operations Center (e.g., `Run Now`, `Revoke`, `Approve selected`, `Dispatch Matrix`).
- **Security & RBAC Matrix**: Required roles (`creator`, `approver`, `operator`, `admin`) per endpoint.
- **Test Metrics**: Exact test pass counts and module catalogs.

### Mandatory Documentation Catalog:
- `README.md` (Main entrypoint: sync release version and technical highlights)
- `DOCS/OVERVIEW.md` (Index of documents and version milestones)
- `DOCS/API.md` (Complete OpenAPI specifications, payloads, responses, and RBAC matrix)
- `DOCS/ARCHITECTURE.md` (Architecture diagrams, sequence flows, and component specs)
- `DOCS/CONFIGURATION.md` (Environment variables, Docker Compose, K8s, and Helm values)
- `DOCS/DATA_MODEL.md` (Database models, tables, columns, and metadata contracts)
- `DOCS/IMPLEMENTATION_STATUS.md` (Completed capability matrix and candidate roadmap)
- `DOCS/ROADMAP.md` (Historical version progression and future roadmap)
- `DOCS/RUNBOOK.md` (SRE operations, failover procedures, and troubleshooting)
- `DOCS/SECURITY_AND_POLICY.md` (Security policies, threat model, DLP, and KMS governance)
- `DOCS/OBSERVABILITY.md` (Tracing, Prometheus metrics, and alerting rules)
- `DOCS/TEST_REPORT.md` (Verified test benchmarks and real browser execution logs)
- `DOCS/USE_CASES.md` (Enterprise real-world patterns and operational cases)
- `DOCS/DEVELOPMENT.md` (Development environment setup and test catalogs)
- `DOCS/manual_test.md` (Step-by-step UI manual test walkthrough, checklist, and script)

All documentation must describe actual runtime behavior rather than hypothetical expectations. Preserve historical version context and evolution sections; do not wholesale delete historical context unless obsolete or inaccurate.

---

## 5. Project-Specific Operational Notes

- **End-of-Turn Checklist**:
  1. Confirm all documentation in `DOCS/` matches current code (routes, fields, schemas, UI labels, test metrics).
  2. Explain manual UI verification steps to the user and ensure `DOCS/manual_test.md` is updated.
- `README.md` is the primary showcase. Keep it synchronized with current capabilities, badges, and architecture diagrams.
- `DOCS/OVERVIEW.md` serves as the documentation directory index; do not create duplicate `DOCS/README.md`.
- `/operations` (Operations Center) is the primary operations hub since v1.0.
- If architectural or UI diagrams are generated, save them under `DOCS/assets/` with descriptive filenames.
- SkillHub currently focuses on capability metadata resolution and does not execute untrusted third-party code.
- If Docker Compose encounters stale Kafka / Zookeeper sessions, recover via:
  ```powershell
  docker compose restart zookeeper kafka api worker
  ```
- Always communicate clearly to the user what was modified, what was tested, and any remaining operational boundaries.

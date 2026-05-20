# Enterprise Browser Agent Platform

Production-grade scaffold for a Browser Agent platform built around:

- FastAPI control plane
- PostgreSQL system of record
- Kafka event bus
- Redis locks / short-lived state / rate limiting
- Playwright sandbox execution
- Evaluator for result verification
- SkillHub for versioned capability registration
- Audit trail and artifact storage
- Policy engine for domain / action / risk gating

## Included

- Task lifecycle API
- Skill registry API
- Approval gate
- Kafka-based orchestration
- Browser runner worker
- Artifact persistence
- v0.2 lifecycle observability with pending approval, queued execution, failed task metadata, correlation IDs, metrics, audit coverage, and a local dashboard
- v0.2 approval policy flow for high-risk and sensitive tasks
- SQL schema and Alembic migration skeleton
- Dockerized local stack
- Minimal tests

## Not included

- LLM provider integration is abstracted behind an interface.
- A production human-in-the-loop UI with auth/RBAC is not implemented. The local v0.2 Dashboard is included for testing and observation.
- Kubernetes manifests are not included in this package.

## Architecture

```text
Client -> FastAPI -> Postgres
                  -> Kafka -> Worker -> Playwright sandbox -> Evaluator -> Postgres / Artifacts
                  -> Redis for locks and ephemeral state
```

## Quick start

### 1) Copy env

```bash
cp .env.example .env
```

### 2) Start stack

```bash
docker compose up --build
```

### 3) Open the demo UI

Open:

```text
http://localhost:8000/demo
```

Use the v0.2 Dashboard to create allowlisted, high-risk, sensitive-instruction, or blocked-domain tasks. The dashboard can approve `pending_approval` tasks and shows task status, policy reason, metrics, audit timeline, evaluation result, browser steps, screenshot preview, and HTML artifact links.

### 4) Create a task manually

```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H 'Content-Type: application/json' \
  -d '{
    "title":"Collect pricing",
    "instructions":"Open the allowlisted sites, compare pricing, and report results.",
    "priority":5,
    "risk_level":"medium",
    "metadata":{"domains":["example.com"],"output_format":"json"}
  }'
```

### 5) Approve the task

```bash
curl -X POST http://localhost:8000/v1/tasks/<TASK_ID>/approve \
  -H 'Content-Type: application/json' \
  -d '{"approved_by":"ops@example.com","note":"Approved for execution"}'
```

## Services

| Service | Purpose |
|---|---|
| api | Control plane and task entrypoint |
| worker | Consumes Kafka events and executes browser tasks |
| postgres | System of record |
| redis | Locks, dedupe, short-lived state |
| kafka | Event stream |
| minio | Planned object storage; current artifact backend is local filesystem |

## Production notes

### Security
- Use per-tenant allowlists.
- Store secrets in a vault, not in Postgres.
- Keep browser sessions ephemeral.
- Require approval or hard-block login/payment flows by policy.
- Require approval for high-risk actions.

### Reliability
- All task events are idempotent.
- Task execution uses a retry budget.
- Dead-letter queue captures poisoned messages.
- Evaluator is decoupled from execution.

### Observability
- Structured JSON logs
- Health endpoints
- Metrics endpoint. In Docker Compose, metrics are process-local, so API `/metrics` does not automatically aggregate worker counters.
- Task-level audit trail

## Project layout

```text
src/browser_agent/
  api.py
  app.py
  db.py
  models.py
  schemas.py
  policy.py
  kafka.py
  storage.py
  evaluator.py
  skillhub.py
  orchestrator.py
  services/
worker/
alembic/
sql/
tests/
```

## Suggested next steps

1. Add SSO / OIDC.
2. Add a real planner backed by your preferred LLM.
3. Add per-action policy rules and production approval UI with auth/RBAC.
4. Add K8s manifests and HPA.
5. Add replay UI for browser session artifacts.

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
- SQL schema and Alembic migration skeleton
- Dockerized local stack
- Minimal tests

## Not included

- LLM provider integration is abstracted behind an interface.
- Human-in-the-loop UI is not implemented.
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

Click **Run demo**. The console creates and approves an allowlisted `https://example.com` task, then shows the task status, evaluation result, browser steps, screenshot preview, and HTML artifact link.

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
| minio | Artifact storage |

## Production notes

### Security
- Use per-tenant allowlists.
- Store secrets in a vault, not in Postgres.
- Keep browser sessions ephemeral.
- Block login/payment flows by default.
- Require approval for high-risk actions.

### Reliability
- All task events are idempotent.
- Task execution uses a retry budget.
- Dead-letter queue captures poisoned messages.
- Evaluator is decoupled from execution.

### Observability
- Structured JSON logs
- Health endpoints
- Metrics endpoint
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
3. Add per-action policy rules and approval UI.
4. Add K8s manifests and HPA.
5. Add replay UI for browser session artifacts.

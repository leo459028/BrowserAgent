# BrowserAgent

<div align="center">

[![License](https://img.shields.io/badge/License-Apache_2.0-blue.svg)](https://opensource.org/licenses/Apache-2.0)
[![Python Version](https://img.shields.io/badge/python-3.12+-blue.svg)](https://www.python.org/downloads/)
[![CI Status](https://img.shields.io/badge/CI-Passing-brightgreen.svg)](https://github.com/leo459028/BrowserAgent/actions)
[![AI Agent Safety](https://img.shields.io/badge/AI_Safety-Strict_HITL_%26_DLP-success.svg)](#core-safety-pillars)
[![Architecture](https://img.shields.io/badge/Architecture-Event--Driven-orange.svg)](#architecture-overview)
[![Deployment](https://img.shields.io/badge/Deploy-Docker_%7C_K8s_%7C_Helm-blueviolet.svg)](#quick-start)

**The Enterprise Open-Source Platform for Safe, Auditable, and Human-in-the-Loop Browser Agents**

*Bridging autonomous AI agency and rigorous operational governance with real-time remote takeover, zero-trust DLP masking, KMS session vaults, and full-fidelity observability.*

[Operations Center Preview](#operations-center) • [Architecture](#architecture-overview) • [Quick Start](#quick-start) • [Agent Safety Pillars](#core-safety-pillars) • [Documentation](DOCS/OVERVIEW.md)

</div>

---

## What is BrowserAgent?

Autonomous browser agents possess immense potential for automating repetitive web workflows—such as inspecting partner portals, auditing SaaS dashboards, extracting regulated reports, and performing production smoke tests. However, deploying unconstrained AI agents in enterprise environments introduces critical risks: **prompt injection vulnerabilities, unauthorized high-risk actions, unmasked credential leakage, and silent execution failures**.

**BrowserAgent (v1.4.2)** solves this fundamental safety dilemma. Rather than treating browser automation as a black-box script, BrowserAgent provides an enterprise-grade control plane that enforces **strict human-in-the-loop (HITL) gates, zero-trust data loss prevention (DLP), cryptographic credential governance, and full-fidelity execution replay**.

Every browser action is governed, audited, observable, and instantly interruptible by human operators.

---

## Core Safety Pillars

```
+-----------------------------------------------------------------------------------+
|                            AI AGENT SAFETY BOUNDARY                               |
+-----------------------------------------------------------------------------------+
|  [ Risk Evaluation Gate ]  -->  [ Zero-Trust Dynamic DLP ]  -->  [ Session Vault ]  |
|   (Low / Med / High / Crit)      (CSS Blurring & Redaction)      (KMS Envelope Enc) |
+-----------------------------------------------------------------------------------+
|  [ Bidirectional Remote Takeover ]  <====>  [ Deterministic Heuristic Healing ]   |
|   (Interactive Pause/Click/Type)             (DOM Multi-attribute Similarity)     |
+-----------------------------------------------------------------------------------+
```

### 1. Bidirectional Remote Takeover (HITL)
High-risk operations and complex validation barriers (such as CAPTCHAs, 2FA challenges, or irreversible financial actions) should not be blindly entrusted to autonomous agents. BrowserAgent provides a low-latency bidirectional WebSocket control channel (`WS /v1/tasks/{id}/live-stream` & `POST /v1/tasks/{id}/interact`), allowing human operators to:
- Pause live execution at any moment (`POST /v1/tasks/{id}/pause`).
- Remotely interact with the browser canvas via mouse clicks and keyboard typing.
- Safely resume automation (`POST /v1/tasks/{id}/resume`) once the barrier is cleared, with every second of human intervention recorded in audit trails.

### 2. Zero-Trust Dynamic Data Loss Prevention (DLP)
Prevents sensitive enterprise data from leaking into execution artifacts, screenshots, logs, or external models:
- **Pixel-Level Blurring**: Automatically injects dynamic CSS Gaussian blur masks (`filter: blur(8px)`) into password fields and confidential DOM nodes before rendering screenshots or video frames.
- **Regex Secret Redaction**: Automatically scrubs Bearer Tokens, API keys, private keys, and session cookies from task metadata, audit logs, and downloaded artifacts.

### 3. Cryptographic Session Vault (KMS Envelope Encryption)
Eliminates cleartext credential storage for authenticated browser sessions. Browser storage states (`cookies`, `localStorage`, `sessionStorage`) are encrypted at rest using AES-256-GCM envelope encryption backed by:
- **Local Keystore** (AES-256 Master Key)
- **AWS KMS** (`kms:GenerateDataKey`, `kms:Decrypt`)
- **HashiCorp Vault** (Transit Secrets Engine)
- Enforces strict tenant isolation using `tenant_id` as Additional Authenticated Data (AAD) to prevent cross-tenant token substitution.

### 4. Cross-Browser Matrix Execution Engine
Natively supports concurrent execution across **Chromium**, **Firefox**, and **WebKit** (`POST /v1/tasks/matrix`). Aggregates cross-engine verdicts, duration deltas, rendering screenshots, and self-healing events in a single unified comparison view.

### 5. Deterministic Heuristic Self-Healing
Websites change dynamically. Rather than calling external, unconstrained, high-latency vision LLMs that could introduce unpredictability, BrowserAgent implements a local multi-tier heuristic cascade (semantic roles, text content, and DOM structural similarity) to recover broken selectors deterministically and safely.

---

## Architecture Overview

BrowserAgent is built upon a decoupled, event-driven microservices architecture designed for resilience and horizontal scalability:

```
                                  +-----------------------------+
                                  |   Enterprise Operators /    |
                                  |     Identity Provider       |
                                  +--------------+--------------+
                                                 | (OIDC PKCE / JWKS)
                                                 v
+-----------------------------------------------------------------------------------------------+
|                                    API CONTROL PLANE (FastAPI)                                 |
|  - Auth & RBAC (Creator / Approver / Operator / Admin)    - Task Lifecycle & Approval Gates    |
|  - Scheduled Tasks Dispatcher (Cron & Redis Lock)         - KMS Cryptographic Session Vault   |
|  - Production Alerting Center (7 Real-time Rules)         - Distributed Tracing (OTEL OTLP)   |
|  - Live WebSocket Streamer & Takeover Controller          - Operations Center (/operations)   |
+------------------------------------------------+----------------------------------------------+
                                                 |
                   +-----------------------------+-----------------------------+
                   | (Task Events)                                             | (Telemetry)
                   v                                                           v
       +-----------------------+                                   +-----------------------+
       |   Apache Kafka Bus    |                                   |  PostgreSQL / Redis   |
       | agent.tasks.{high,    |                                   | Metadata, Idempotency,|
       |   queued, batch, dlq} |                                   | Distributed Leases    |
       +-----------+-----------+                                   +-----------------------+
                   |
                   | (Priority Partitioning)
                   v
+-----------------------------------------------------------------------------------------------+
|                                    WORKER EXECUTION FLEET                                     |
|  - Playwright Multi-Engine Runner (Chromium / Firefox / WebKit)                               |
|  - Zero-Trust Dynamic DLP Masking & Regex Redaction                                           |
|  - Heuristic DOM Selector Self-Healing Cascade                                                |
|  - Full-Motion WebM Video Recorder & Frame Streamer                                           |
|  - S3 / MinIO Encrypted Artifact Store                                                        |
+-----------------------------------------------------------------------------------------------+
```

For the full architectural specification and component interaction diagrams, see [DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md).

Architecture Diagram:
![BrowserAgent Architecture](DOCS/assets/browseragent-architecture-v1.4en.png)

---

## Operations Center

The primary operational hub is accessible at:
```text
http://localhost:8000/operations
```

The **Operations Center** consolidates all governance, safety, and telemetry workflows into a single responsive dashboard:
- **Task Lifecycle & Approvals**: View pending tasks, risk evaluations, and perform one-click approvals.
- **Interactive Remote Takeover (HITL)**: Stream live browser canvases via WebSockets, pause runs, click elements, and inject keystrokes in real time.
- **Cross-Browser Matrix Comparison**: Compare execution times, verdicts, and screenshots across Chromium, Firefox, and WebKit.
- **Production Readiness & Health**: Real-time status checks for DB, Kafka, Redis, S3/MinIO, Worker identities, and OIDC auth modes.
- **Production Alerting Center**: 7 real-time rule evaluations with non-blocking asynchronous Webhook dispatch (Slack/Discord).
- **Execution Video & Step Replay**: WebM full-session video player with step-level DOM diffs, execution timing, and screenshot thumbnails.
- **Distributed Trace Inspector**: Cross-process span hierarchy visualization with W3C `traceparent` context propagation.
- **Dead Letter Queue (DLQ) & Quarantine**: Replay failed tasks individually or in bulk, and isolate toxic payloads into quarantine.

---

## Quick Start

### 1. Run with Docker Compose (Recommended)

Clone the repository and spin up the complete production-grade stack (API, Worker, PostgreSQL, Kafka, Redis, MinIO):

```bash
# Clone the repository
git clone https://github.com/leo459028/BrowserAgent.git
cd BrowserAgent

# Configure environment variables
cp .env.example .env

# Build and start services
docker compose up -d --build
```

Access the Operations Center at:
```text
http://localhost:8000/operations
```

Health check verification:
```bash
curl http://localhost:8000/healthz
curl http://localhost:8000/readyz
```

### 2. Local Python Development Setup

If running without Docker containers:

```bash
# Create and activate virtual environment
python -m venv .venv
source .venv/bin/activate  # On Windows: .\.venv\Scripts\Activate.ps1

# Install dependencies and Playwright browsers
pip install --upgrade pip
pip install -r requirements.txt
playwright install --with-deps chromium firefox webkit

# Run tests
pytest -q
```

---

## API Usage Examples

### 1. Acquire Local Developer Token
```bash
TOKEN=$(curl -s -X POST http://localhost:8000/v1/auth/local-token \
  -H "Content-Type: application/json" \
  -d '{"role":"creator"}' | jq -r .access_token)
```

### 2. Submit a Governed Browser Task
```bash
curl -X POST http://localhost:8000/v1/tasks \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -H "Idempotency-Key: task-audit-demo-001" \
  -d '{
    "title": "Audit Internal Portal",
    "instructions": "Navigate to the partner dashboard and capture compliance proof.",
    "priority": 1,
    "risk_level": "medium",
    "browser_engine": "chromium",
    "metadata": {
      "domains": ["example.com"],
      "start_url": "https://example.com"
    }
  }'
```

### 3. Dispatch a Multi-Browser Matrix Task
```bash
curl -X POST http://localhost:8000/v1/tasks/matrix \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "title": "Cross-Engine Layout Verification",
    "instructions": "Render the public landing page across all major browser engines.",
    "engines": ["chromium", "firefox", "webkit"],
    "metadata": {
      "start_url": "https://example.com"
    }
  }'
```

---

## Verification & Testing Suite

BrowserAgent includes a comprehensive automated test suite consisting of **20 modules and 105 tests** covering authentication, cryptographic storage, Kafka flows, Playwright execution, and UI rendering:

```bash
# Execute full test suite
pytest -q

# Run Python compilation verification
python -m compileall src tests worker alembic

# Check git whitespace compliance
git diff --check
```

For actual verification benchmarks and test outputs, refer to [DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md).

---

## Kubernetes & Enterprise Helm 3 Deployment

Production manifests and Helm charts are provided under `deploy/`:

```bash
# Validate Kubernetes Kustomize manifests
kubectl kustomize deploy/k8s/

# Lint and template the Helm Chart
helm lint deploy/helm/browser-agent
helm template deploy/helm/browser-agent
```

For automated GitOps deployment, an ArgoCD application manifest is provided at `deploy/gitops/argocd-application.yaml`.

---

## Documentation Index

| Document | Focus Area |
| :--- | :--- |
| **[DOCS/OVERVIEW.md](DOCS/OVERVIEW.md)** | Architectural summary, milestone evolution, and documentation map |
| **[DOCS/API.md](DOCS/API.md)** | Complete OpenAPI specifications, payloads, responses, and RBAC matrix |
| **[DOCS/ARCHITECTURE.md](DOCS/ARCHITECTURE.md)** | Deep-dive system architecture, state machines, and sequence flows |
| **[DOCS/CONFIGURATION.md](DOCS/CONFIGURATION.md)** | Environment variable reference, secrets management, and Helm values |
| **[DOCS/DATA_MODEL.md](DOCS/DATA_MODEL.md)** | Database schemas, SQLAlchemy models, and metadata contracts |
| **[DOCS/SECURITY_AND_POLICY.md](DOCS/SECURITY_AND_POLICY.md)** | Threat models, Zero-Trust DLP, RBAC boundaries, and KMS key governance |
| **[DOCS/OBSERVABILITY.md](DOCS/OBSERVABILITY.md)** | OpenTelemetry tracing, Prometheus metrics, alerting rules, and audit trails |
| **[DOCS/USE_CASES.md](DOCS/USE_CASES.md)** | Enterprise real-world patterns (HITL CAPTCHA, Cross-browser matrix, DLP) |
| **[DOCS/RUNBOOK.md](DOCS/RUNBOOK.md)** | SRE operations runbook, cluster failover procedures, and troubleshooting |
| **[DOCS/DEVELOPMENT.md](DOCS/DEVELOPMENT.md)** | Local development environment setup, mock backends, and debugging guide |
| **[DOCS/manual_test.md](DOCS/manual_test.md)** | Step-by-step UI manual testing guide, checklist, and verification scripts |
| **[DOCS/TEST_REPORT.md](DOCS/TEST_REPORT.md)** | Verified test execution logs, coverage metrics, and platform readiness |
| **[DOCS/ROADMAP.md](DOCS/ROADMAP.md)** | Release milestones (v1.0 through v1.4.2) and future v1.5 candidate roadmap |

---

## Open Source Community & Governance

BrowserAgent is open-source software licensed under the **[Apache License 2.0](LICENSE)**.

- **[Contributing Guidelines](CONTRIBUTING.md)**: Guidelines for opening issues, PR conventions, and code review.
- **[Code of Conduct](CODE_OF_CONDUCT.md)**: Community standards and enforcement guidelines.
- **[Security Policy](SECURITY.md)**: Vulnerability disclosure and AI agent safety reporting channels.

---

<div align="center">
<sub>Built with precision for safe, auditable, and production-ready browser agent workflows.</sub>
</div>

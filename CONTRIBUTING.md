# Contributing to BrowserAgent

Thank you for your interest in contributing to **BrowserAgent**! 

BrowserAgent is dedicated to building an enterprise-grade, transparent, and auditable browser automation platform that prioritizes **AI Agent Safety**, **Zero-Trust Data Loss Prevention (DLP)**, and **Human-in-the-Loop (HITL)** governance.

Whether you are fixing bugs, proposing new capabilities, improving documentation, or hardening agent safety policies, we welcome your contributions!

---

## Code of Conduct

All contributors and participants must adhere to our [Code of Conduct](CODE_OF_CONDUCT.md). Please treat all community members with respect and professionalism.

---

## Getting Started

### Prerequisites

- **Python**: 3.12+
- **Node.js**: Required only for optional Playwright client dev tools
- **Docker & Docker Compose**: Recommended for local integration testing (PostgreSQL, Kafka, Redis, MinIO)
- **Git**

### Local Development Setup

1. **Fork and Clone the Repository**:
   ```bash
   git clone https://github.com/<your-username>/BrowserAgent.git
   cd BrowserAgent
   ```

2. **Set up Virtual Environment**:
   ```bash
   python -m venv .venv
   # Windows (PowerShell)
   .\.venv\Scripts\Activate.ps1
   # Linux / macOS
   source .venv/bin/activate
   ```

3. **Install Dependencies**:
   ```bash
   pip install --upgrade pip
   pip install -r requirements.txt
   playwright install --with-deps chromium firefox webkit
   ```

4. **Initialize Environment Variables**:
   ```bash
   cp .env.example .env
   ```

5. **Start Infrastructure Services (Optional but recommended)**:
   ```bash
   docker compose up -d postgres redis minio kafka
   ```

---

## Development Workflow

### Branching Strategy

- Always create feature branches off `main`:
  ```bash
  git checkout -b feat/your-feature-name
  # or
  git checkout -b fix/your-bug-fix
  ```

### Commit Message Conventions

We follow the [Conventional Commits](https://www.conventionalcommits.org/) specification:

- `feat(scope)`: A new feature or capability
- `fix(scope)`: A bug fix
- `docs(scope)`: Documentation changes only
- `test(scope)`: Adding or updating tests
- `refactor(scope)`: Code changes that neither fix bugs nor add features
- `chore(scope)`: Build process, dependencies, or tool configurations

*Examples:*
- `feat(hitl): add keyboard shortcut injection to remote takeover channel`
- `fix(dlp): resolve edge case in JWT token regex redaction`
- `docs(api): update OpenAPI schemas for session vault validate endpoint`

---

## Quality and Safety Standards

### AI Agent Safety Guidelines

Because BrowserAgent controls live web browsers and handles sensitive operations, all code changes touching browser execution or task evaluation must comply with our Agent Safety Principles:

1. **Strict Human-in-the-Loop (HITL) Gate**: High-risk actions must never execute without explicit operator approval (`pending_approval`).
2. **Zero-Trust DLP Enforcement**: Secrets (passwords, tokens, cookies, PII) must be masked in memory, redacted from logs, and blurred in screenshots/video replays.
3. **Session Vault Isolation**: Browser storage states containing sensitive cookies must be protected with cryptographic KMS envelope encryption and scoped to specific tenants.
4. **Deterministic Heuristics**: Automated fallbacks and self-healing mechanisms must operate transparently with structured audit logs.

### Verification Checklist

Before submitting a Pull Request, ensure that:

```bash
# 1. Run all unit and integration tests
pytest -q

# 2. Compile all Python packages
python -m compileall src tests worker alembic

# 3. Check for whitespace or formatting issues
git diff --check
```

---

## Submitting Pull Requests

1. **Push your branch** to your fork:
   ```bash
   git push origin feat/your-feature-name
   ```
2. **Open a Pull Request** against the `main` branch of `BrowserAgent`.
3. **Fill out the Pull Request Template**:
   - Provide a clear summary of the changes and motivation.
   - Specify whether the changes impact security, API schemas, or UI behavior.
   - Attach test execution outputs or screenshots (if UI changes are made).
4. **CI Checks**: Ensure all automated GitHub Actions pass.
5. **Code Review**: At least one maintainer review is required before merging.

---

## Reporting Vulnerabilities

If you discover a security vulnerability or an AI Agent Safety flaw, please do **NOT** open a public issue. Follow the instructions in [SECURITY.md](SECURITY.md) to report it responsibly.

---

Thank you for helping make autonomous browser agents safe, reliable, and auditable for everyone!

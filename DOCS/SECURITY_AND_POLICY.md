# Security, AI Safety & Governance Policies

This document specifies the security boundaries, AI agent safety guardrails, Role-Based Access Control (RBAC) matrix, Zero-Trust Data Loss Prevention (DLP) architecture, and cryptographic key governance enforced by BrowserAgent.

---

## AI Agent Safety & Threat Model

Deploying autonomous browser agents in production environments presents significant risks if left unconstrained. BrowserAgent enforces a defense-in-depth safety architecture:

```
+---------------------------------------------------------------------------------------------------+
|                                     INCOMING AGENT TASK PAYLOAD                                   |
+---------------------------------------------------------------------------------------------------+
                                                  |
                                                  v
                      [ Domain Boundary Gate ] -- (Strict ALLOWLIST_DOMAINS)
                                                  |
                                                  v
                      [ Prompt Injection & Risk Gate ] -- (Evaluate Risk Tiers)
                                                  |
                          +-----------------------+-----------------------+
                          |                                               |
                          | (Risk <= Low)                                 | (Risk >= Medium)
                          v                                               v
                 [ Automatic Queue ]                          [ Human-in-the-Loop Approval Gate ]
                          |                                               | (Operator Approval)
                          +-----------------------+-----------------------+
                                                  |
                                                  v
                                      [ Worker Playwright Execution ]
                                                  |
                                                  +---> [ Zero-Trust Dynamic DLP CSS Blurring ]
                                                  +---> [ Real-Time Reverse Takeover Channel ]
                                                  +---> [ Deterministic Heuristic Self-Healing ]
                                                  |
                                                  v
                                    [ Sanitized Artifact & Audit Store ]
                                  (AES-256-GCM Envelope Encryption + Redaction)
```

---

## Authentication & Role-Based Access Control (RBAC)

BrowserAgent supports multiple enterprise identity modes:

- **`AUTH_MODE=local`**: Issues HS256 developer tokens signed with `APP_SECRET_KEY`. Restricted exclusively to local development and testing.
- **`AUTH_MODE=jwks`**: Verifies external RS256/JWKS tokens via `AUTH_JWKS_URL` or auto-discovered through `AUTH_OIDC_ISSUER_URL`.
- **Enterprise OIDC Authorization Code Flow with PKCE**:
  - Implements OAuth 2.0 / OpenID Connect with **PKCE (RFC 7636)**.
  - Generates high-entropy random `code_verifier` and SHA-256 `code_challenge`, eliminating authorization code interception vulnerabilities.
  - Generates cryptographically secure `state` parameters to prevent Cross-Site Request Forgery (CSRF).
  - Encapsulates authenticated sessions in **HttpOnly, SameSite=Strict** secure cookies (`ba_session`), shielding credentials against XSS theft.

### RBAC Permission Matrix

| Operation / Endpoint Group | `creator` | `approver` | `operator` | `admin` |
| :--- | :---: | :---: | :---: | :---: |
| Create Task / Batch Matrix Task | :white_check_mark: | :x: | :x: | :white_check_mark: |
| Approve Pending Task | :x: | :white_check_mark: | :x: | :white_check_mark: |
| Read Task / Audits / Artifacts | :white_check_mark: | :white_check_mark: | :white_check_mark: | :white_check_mark: |
| Scheduled Tasks (Create / Edit / Pause) | :white_check_mark: | :x: | :x: | :white_check_mark: |
| Scheduled Tasks (Run Now / Trigger) | :white_check_mark: | :x: | :white_check_mark: | :white_check_mark: |
| Inspect Telemetry / Traces / Alerts | :x: | :x: | :white_check_mark: | :white_check_mark: |
| HITL Takeover (Pause / Interact / Resume) | :x: | :x: | :white_check_mark: | :white_check_mark: |
| Online Task Abort | :x: | :x: | :white_check_mark: | :white_check_mark: |
| DLQ Single & Bulk Replay / Quarantine | :x: | :x: | :white_check_mark: | :white_check_mark: |
| Session Vault Validate | :x: | :x: | :white_check_mark: | :white_check_mark: |
| Session Vault One-Click Revoke | :x: | :x: | :x: | :white_check_mark: |
| Alert Webhook Test Dispatch | :x: | :x: | :x: | :white_check_mark: |
| Federation Forced Re-election | :x: | :x: | :x: | :white_check_mark: |
| Register SkillHub Capability | :x: | :x: | :x: | :white_check_mark: |

---

## Zero-Trust Dynamic DLP (Data Loss Prevention)

To prevent confidential enterprise secrets from leaking into execution artifacts, video recordings, or external telemetry pipelines, BrowserAgent implements a 3-tier DLP architecture:

1. **Source-Level CSS Gaussian Blur Masking**:
   - During Playwright page initialization and dynamic navigation, the DLP service automatically injects protective CSS rules into DOM frames: targeting `input[type="password"]` and configured secret selectors with `filter: blur(8px) !important`.
   - All live WebSocket frames, WebM recordings, and PNG screenshots capture blurred pixels at the source. Even if recorded media is exfiltrated, cleartext credentials cannot be recovered.
2. **Dynamic Regex Secret Redaction**:
   - Outbound text streams, step outputs, and terminal logs are continuously filtered against high-entropy patterns (Bearer Tokens, JWTs, OpenAI API keys, AWS access keys, PEM certificates), replacing matches with `[REDACTED_TOKEN]` or `sk-[REDACTED_KEY]`.
3. **Recursive Metadata Sanitization**:
   - Before task metadata, step payloads, or audit trails are persisted to PostgreSQL or emitted to OpenTelemetry spans, dictionary keys containing sensitive names (`password`, `token`, `secret`, `authorization`) are scrubbed recursively.

---

## Bidirectional Remote Takeover (HITL) Governance

1. **Strict Tenant Scoping**: All takeover endpoints (`POST /v1/tasks/{id}/{pause,interact,resume}`) enforce strict matching between token tenant and task tenant, preventing cross-tenant interaction injection.
2. **Action Boundary Validation**:
   - Restricts commands strictly to validated action types (`click`, `type`, `press`).
   - Mouse click coordinates (X, Y) are strictly validated against active viewport boundaries.
   - Text keystrokes undergo DLP regex sanitization before injection.
3. **Automated Timeout Protection**:
   - Paused takeover states enforce a maximum timeout (`REMOTE_TAKEOVER_TIMEOUT_SECONDS`, default: 300s). If an operator abandons a paused session, the system automatically aborts or resumes the workflow, logging an audit exception.
4. **Non-Repudiation Audit Logging**:
   - Every human intervention records operator identity, IP address, timestamps, intervention duration, and discrete actions performed.

---

## Session Vault KMS Envelope Encryption

Playwright `storage_state` captures live authentication cookies and `localStorage` tokens, constituting high-value secrets.

- **Envelope Encryption**:
  - Each session payload is encrypted using a unique, cryptographically random 256-bit Data Encryption Key (DEK).
  - The plaintext DEK encrypts the session state using `AES-256-GCM`.
  - **Tenant Isolation via AAD**: Binds the `tenant_id` as Additional Authenticated Data (AAD) in the AES-GCM cipher. Any cross-tenant tampering or token substitution fails decryption verification immediately.
  - The DEK itself is encrypted using a Key Encryption Key (KEK) managed by the designated KMS provider (Local Keystore, AWS KMS, or HashiCorp Vault).
- **Session Revocation**: One-click revocation (`DELETE /v1/sessions/{session_name}`) requires `admin` role, logs a `session.revoked` audit entry, and immediately prevents worker reuse.

---

## Policy Engine & Network Egress Boundaries

- **Strict Domain Boundary**: Tasks cannot navigate outside `ALLOWLIST_DOMAINS`. Unlisted domain requests are rejected immediately.
- **Risk Evaluation Gates**: Tasks evaluated with elevated risk levels automatically enter `pending_approval` and require authorized operator sign-off before execution.
- **Prompt Injection Defense**: Evaluates task instructions against adversarial injection signatures before plan dispatch.

---

## Production Security Checklist

- [ ] Do not use default `APP_SECRET_KEY` in production environments.
- [ ] Set `AUTH_LOCAL_TOKENS_ENABLED=false` and configure `AUTH_MODE=jwks` with a production IdP.
- [ ] Ensure `RELIABILITY_STORE=redis` and `ARTIFACT_BACKEND=s3`.
- [ ] For Kubernetes deployments, mount sensitive variables from Kubernetes Secrets backed by cloud KMS.
- [ ] Enable `DLP_ENABLED=true`, `DLP_MASK_PASSWORDS=true`, and `DLP_REDACT_TOKENS=true`.

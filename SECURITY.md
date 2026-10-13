# Security Policy

The BrowserAgent project takes the security of autonomous agent execution, browser automation, and sensitive credential governance seriously. This document outlines our security policies and procedures for reporting potential vulnerabilities.

---

## Supported Versions

We provide security updates and critical patches for the following versions:

| Version | Supported          | Security Maintenance Level |
| ------- | ------------------ | -------------------------- |
| 1.4.x   | :white_check_mark: | Active support & patches   |
| 1.3.x   | :white_check_mark: | Critical security fixes    |
| < 1.3.0 | :x:                | End of Life (upgrade rec.) |

---

## Reporting a Vulnerability

If you discover a security vulnerability or an AI Agent Safety flaw (such as prompt injection escape, DLP bypass, unauthorized takeover, or credential leakage), please **do not create a public issue**.

Instead, please report the vulnerability privately via one of the following methods:

1. **GitHub Private Vulnerability Reporting**:
   Navigate to the **Security** tab of this repository, select **Advisories**, and click **Report a vulnerability**.
2. **Email**:
   Send an encrypted or detailed report to `security@browseragent.dev`.

### What to Include in Your Report

To help us triage and resolve the issue quickly, please provide:

- A clear description of the vulnerability.
- Steps to reproduce the issue (including sample task payload or curl command).
- The affected component (e.g., API Control Plane, Worker Runner, DLP Shield, Session Vault KMS).
- Potential impact (e.g., credential disclosure, privilege escalation, unauthorized browser action).
- Any proposed mitigations or proof-of-concept scripts.

---

## Response Process & Timeline

1. **Acknowledgment**: We aim to acknowledge receipt of your vulnerability report within **48 hours**.
2. **Triage & Assessment**: We will assess the severity, reproduce the issue, and maintain open communication regarding the patch plan.
3. **Remediation**: A fix will be developed in a private security fork.
4. **Public Disclosure**: Once a patch is released (typically within 14–30 days depending on complexity), a Common Vulnerabilities and Exposures (CVE) or GitHub Security Advisory will be published, crediting the reporter if desired.

---

## AI Agent Safety Principles

BrowserAgent is explicitly designed as a safety barrier against autonomous agent misbehavior:

- **Human-in-the-Loop (HITL)**: Any browser interaction marked with elevated risk levels is gated by human approval.
- **Zero-Trust Data Loss Prevention (DLP)**: Passwords and tokens must be dynamically masked before leaving the browser context.
- **Cryptographic Isolation**: Session cookies are encrypted at rest using AES-256-GCM envelope encryption.
- **Strict Network Egress Filtering**: Browser tasks are restricted to allowlisted domain boundaries (`ALLOWLIST_DOMAINS`).

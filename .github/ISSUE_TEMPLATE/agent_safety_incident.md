---
name: AI Agent Safety Incident / Feedback
about: Report a potential agent safety issue, guardrail bypass, or HITL policy escape
title: "[SAFETY] "
labels: ["agent-safety", "policy", "triage"]
assignees: ""
---

> **NOTE**: If this involves an active exploitable security vulnerability or credential leak, please report it privately according to [SECURITY.md](SECURITY.md).

## Safety Concern Classification
- [ ] Human-in-the-Loop (HITL) bypass or failure to pause
- [ ] DLP mask failure (sensitive field unblurred or leaked into artifacts)
- [ ] Domain allowlist or network boundary escape
- [ ] Session Vault credential leakage or cross-tenant exposure
- [ ] Adversarial prompt injection susceptibility via web page content
- [ ] Other safety or governance concern

## Incident Description
Explain what occurred during the agent's interaction with the web browser and why it constitutes a safety or alignment issue.

## Task Payload / Safety Context
Provide the sanitized task instructions and domain metadata:
```json
{
  "instructions": "...",
  "risk_level": "...",
  "metadata": {}
}
```

## Guardrail Failure Analysis
- What safety guardrail should have prevented this action?
- How did the agent or runner behave unexpectedly?

## Recommended Safety Enhancement
What heuristic, policy rule, or DLP filter should be implemented to prevent this occurrence?

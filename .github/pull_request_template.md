## Summary of Changes
Provide a brief summary of what this PR introduces, fixes, or refactors.

## Motivation & Issue Reference
- Resolves: #[issue-number]
- Why is this change necessary?

## Type of Change
- [ ] Bug fix (non-breaking change which fixes an issue)
- [ ] New feature (non-breaking change which adds functionality)
- [ ] AI Agent Safety / DLP hardening
- [ ] Performance optimization / Refactoring
- [ ] Documentation update
- [ ] Breaking change (fix or feature that would cause existing functionality to not work as expected)

## Safety & Governance Review
- [ ] **Human-in-the-Loop (HITL)**: Does this change respect human approval gates and remote takeover mechanisms?
- [ ] **Data Loss Prevention (DLP)**: Are all sensitive credentials, tokens, or PII dynamically redacted or masked?
- [ ] **Session Vault**: Are session credentials cryptographically isolated using KMS envelope encryption?
- [ ] **Domain Guardrails**: Does this change enforce the strict `ALLOWLIST_DOMAINS` boundary?

## Testing & Verification
Describe the tests you ran to verify your changes:
- [ ] Local unit and integration tests passed: `pytest -q`
- [ ] Compilation check passed: `python -m compileall src tests worker alembic`
- [ ] Whitespace check passed: `git diff --check`
- [ ] End-to-end / Operations Center verification performed (if applicable)

## Checklist
- [ ] My code adheres to the style guidelines of this project
- [ ] I have performed a self-review of my own code
- [ ] I have commented my code, particularly in hard-to-understand areas
- [ ] I have updated the documentation in `DOCS/` corresponding to these changes
- [ ] My changes generate no new warnings or lint errors
- [ ] Existing tests pass locally with my changes

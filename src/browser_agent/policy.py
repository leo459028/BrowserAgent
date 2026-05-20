from dataclasses import dataclass
from .config import get_settings

@dataclass(frozen=True)
class PolicyDecision:
    allowed: bool
    reason: str
    requires_approval: bool = False

BLOCKED_KEYWORDS = {"payment", "transfer", "wire", "bank", "password", "mfa", "otp", "login"}

def evaluate_task_policy(task: dict) -> PolicyDecision:
    settings = get_settings()
    risk_level = task.get("risk_level", "low")
    metadata = task.get("metadata", {}) or {}
    domains = metadata.get("domains", [])

    if any(d not in settings.allowlist_domain_set for d in domains):
        return PolicyDecision(False, "domain not allowlisted", False)

    if risk_level in {"high", "critical"}:
        return PolicyDecision(False, "high-risk task requires manual approval", True)

    instructions = (task.get("instructions") or "").lower()
    if any(keyword in instructions for keyword in BLOCKED_KEYWORDS):
        return PolicyDecision(False, "sensitive action requires manual approval", True)

    return PolicyDecision(True, "allowed", False)

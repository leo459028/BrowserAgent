import re
from dataclasses import dataclass

SUSPICIOUS_PATTERNS = [
    r"ignore previous instructions",
    r"reveal system prompt",
    r"exfiltrate",
    r"bypass",
    r"steal",
]

@dataclass(frozen=True)
class SecurityFinding:
    allowed: bool
    reason: str
    risk: str = "low"

def inspect_instructions(text: str) -> SecurityFinding:
    lowered = text.lower()
    for pattern in SUSPICIOUS_PATTERNS:
        if re.search(pattern, lowered):
            return SecurityFinding(False, f"blocked pattern: {pattern}", "high")
    return SecurityFinding(True, "ok", "low")

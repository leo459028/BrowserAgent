from __future__ import annotations

from dataclasses import dataclass

@dataclass(frozen=True)
class EvaluationResult:
    score: float
    verdict: str
    checks: list[dict]

def evaluate_execution(task: dict, result: dict) -> EvaluationResult:
    checks = []
    score = 0.0

    page_url = result.get("final_url")
    html = result.get("html", "")
    artifacts = result.get("artifacts", [])

    if page_url:
        checks.append({"check": "final_url_present", "passed": True, "value": page_url})
        score += 25
    else:
        checks.append({"check": "final_url_present", "passed": False})
    if html:
        checks.append({"check": "html_captured", "passed": True, "value_len": len(html)})
        score += 25
    else:
        checks.append({"check": "html_captured", "passed": False})
    if artifacts:
        checks.append({"check": "artifacts_written", "passed": True, "count": len(artifacts)})
        score += 25
    else:
        checks.append({"check": "artifacts_written", "passed": False})

    target = (task.get("metadata") or {}).get("expected_domain")
    if target and page_url and target in page_url:
        checks.append({"check": "expected_domain", "passed": True, "value": target})
        score += 25
    elif target:
        checks.append({"check": "expected_domain", "passed": False, "value": target})

    verdict = "pass" if score >= 75 else "warn" if score >= 50 else "fail"
    return EvaluationResult(score=score, verdict=verdict, checks=checks)

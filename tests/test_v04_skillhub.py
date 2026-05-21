from __future__ import annotations

import uuid
from datetime import datetime, timezone
from types import SimpleNamespace

from browser_agent.runner import resolve_plan_step_skills


TENANT_ID = uuid.UUID("00000000-0000-0000-0000-000000000001")


def test_resolve_plan_step_skills_marks_active_skill_as_resolved():
    skill = SimpleNamespace(
        name="browser.goto",
        version="1.2.0",
        entrypoint="browser.goto",
        created_at=datetime.now(timezone.utc),
    )
    resolver = _FakeSkillHub({("browser.goto", None): skill})

    steps = resolve_plan_step_skills(
        [{"action": "goto", "url": "https://example.com"}],
        tenant_id=TENANT_ID,
        skillhub=resolver,
    )

    assert steps[0]["skill"] == {
        "name": "browser.goto",
        "version": "1.2.0",
        "entrypoint": "browser.goto",
        "resolved": True,
    }


def test_resolve_plan_step_skills_uses_requested_version_when_present():
    skill = SimpleNamespace(
        name="browser.screenshot",
        version="2.0.0",
        entrypoint="browser.screenshot",
        created_at=datetime.now(timezone.utc),
    )
    resolver = _FakeSkillHub({("browser.screenshot", "2.0.0"): skill})

    steps = resolve_plan_step_skills(
        [{"action": "screenshot", "skill_version": "2.0.0"}],
        tenant_id=TENANT_ID,
        skillhub=resolver,
    )

    assert resolver.calls == [("browser.screenshot", "2.0.0")]
    assert steps[0]["skill"]["version"] == "2.0.0"
    assert steps[0]["skill"]["resolved"] is True


def test_resolve_plan_step_skills_marks_missing_skill_without_blocking_step():
    resolver = _FakeSkillHub({})

    steps = resolve_plan_step_skills(
        [{"action": "extract_text", "target": "h1"}],
        tenant_id=TENANT_ID,
        skillhub=resolver,
    )

    assert steps[0]["action"] == "extract_text"
    assert steps[0]["skill"] == {
        "name": "browser.extract_text",
        "version": None,
        "entrypoint": "builtin.browser.extract_text",
        "resolved": False,
    }


class _FakeSkillHub:
    def __init__(self, skills):
        self.skills = skills
        self.calls = []

    def resolve(self, tenant_id, name, version=None):
        self.calls.append((name, version))
        return self.skills.get((name, version))

from __future__ import annotations

from browser_agent.planner import build_planner_metadata, deterministic_fallback_plan, validate_plan_output


def test_valid_planner_output_passes_schema_validation():
    output = {
        "goal": "Capture example",
        "version": "heuristic-v0.4",
        "source": "heuristic",
        "steps": [
            {"action": "goto", "url": "https://example.com"},
            {"action": "wait", "ms": 250},
            {"action": "screenshot"},
        ],
        "risk_level": "low",
    }

    validated = validate_plan_output(output)

    assert validated.valid is True
    assert validated.errors == []
    assert [step.action for step in validated.steps] == ["goto", "wait", "screenshot"]
    assert validated.steps[0].input_data == {"action": "goto", "url": "https://example.com"}


def test_missing_required_step_field_records_validation_error():
    output = {
        "goal": "Broken click",
        "version": "heuristic-v0.4",
        "source": "heuristic",
        "steps": [{"action": "click"}],
        "risk_level": "low",
    }

    validated = validate_plan_output(output)

    assert validated.valid is False
    assert validated.errors == [
        {
            "step_no": 1,
            "action": "click",
            "message": "click requires target",
        }
    ]


def test_deterministic_fallback_uses_start_url_when_available():
    fallback = deterministic_fallback_plan(
        {
            "title": "Fallback task",
            "risk_level": "medium",
            "metadata": {"start_url": "https://example.com"},
        }
    )

    assert fallback["source"] == "fallback"
    assert fallback["steps"] == [
        {"action": "goto", "url": "https://example.com"},
        {"action": "screenshot"},
    ]


def test_planner_metadata_records_fallback_and_error_summary():
    invalid_output = {
        "goal": "Broken task",
        "version": "heuristic-v0.4",
        "source": "heuristic",
        "steps": [{"action": "fill", "target": "#q"}],
        "risk_level": "low",
    }

    metadata = build_planner_metadata(
        invalid_output,
        {
            "title": "Broken task",
            "risk_level": "low",
            "metadata": {"start_url": "https://example.com"},
        },
    )

    assert metadata["planner"]["valid"] is False
    assert metadata["planner"]["fallback_used"] is True
    assert metadata["planner"]["validation_errors"] == [
        {
            "step_no": 1,
            "action": "fill",
            "message": "fill requires value",
        }
    ]
    assert metadata["plan"] == [
        {"action": "goto", "url": "https://example.com"},
        {"action": "screenshot"},
    ]

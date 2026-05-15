from browser_agent.evaluator import evaluate_execution

def test_evaluator_passes_with_artifacts():
    result = evaluate_execution(
        {"metadata": {"expected_domain": "example.com"}},
        {"final_url": "https://example.com/a", "html": "<html></html>", "artifacts": [{"type":"screenshot"}]},
    )
    assert result.score >= 75
    assert result.verdict == "pass"

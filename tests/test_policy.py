from browser_agent.policy import evaluate_task_policy

def test_policy_blocks_unallowlisted_domain():
    task = {
        "risk_level": "low",
        "metadata": {"domains": ["evil.com"]},
        "instructions": "hello",
    }
    decision = evaluate_task_policy(task)
    assert not decision.allowed

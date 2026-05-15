from __future__ import annotations

from abc import ABC, abstractmethod

class PlannerClient(ABC):
    @abstractmethod
    def plan(self, task: dict) -> dict:
        raise NotImplementedError

class HeuristicPlanner(PlannerClient):
    def plan(self, task: dict) -> dict:
        instructions = (task.get("instructions") or "").lower()
        metadata = task.get("metadata") or {}
        start_url = metadata.get("start_url")
        plan = []
        if start_url:
            plan.append({"action": "goto", "url": start_url})
        if "login" in instructions:
            plan.append({"action": "wait", "ms": 500})
        plan.append({"action": "screenshot"})
        return {
            "goal": task.get("title"),
            "steps": plan,
            "risk_level": task.get("risk_level", "low"),
        }

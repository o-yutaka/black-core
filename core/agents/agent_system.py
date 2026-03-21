from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus


class AgentSystem:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        strategy = analysis["recommended_strategy"]
        code = self._build_code_task(analysis)
        plan = {
            "strategy": strategy,
            "tasks": [
                {
                    "name": "execute-generated-python",
                    "goal": analysis["goal"],
                    "evidence_count": len(analysis["memory_hits"]),
                    "code": code,
                }
            ],
        }
        self.event_bus.publish("arena.completed", plan)
        return plan

    @staticmethod
    def _build_code_task(analysis: Dict[str, Any]) -> str:
        for hit in analysis["memory_hits"]:
            previous_code = hit.get("context", {}).get("action", {}).get("code")
            if hit.get("success") and previous_code:
                return previous_code

        goal = analysis["goal"].replace('"', "'")
        return (
            "from statistics import mean\n"
            "samples = [3, 5, 8, 13, 21]\n"
            "result = {\n"
            f"    'goal': \"{goal}\",\n"
            "    'sample_count': len(samples),\n"
            "    'average': mean(samples),\n"
            "    'max_value': max(samples),\n"
            "}\n"
            "print(result)\n"
        )

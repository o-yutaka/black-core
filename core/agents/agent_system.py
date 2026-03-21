from __future__ import annotations

from typing import Any, Dict, List

from core.agents.multi_agent_reasoner import MultiAgentReasoner
from core.event_bus import EventBus
from executor.code_generation_engine import CodeGenerationEngine


class AgentSystem:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.reasoner = MultiAgentReasoner()
        self.code_generation_engine = CodeGenerationEngine()

    def plan(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        memory_hints = {
            "successful_strategies": [
                item["strategy"] for item in analysis.get("top_strategies", []) if item.get("win_rate", 0.0) >= 0.5
            ],
            "failed_strategies": analysis.get("failed_strategies", []),
        }

        deliberation = self.reasoner.deliberate(
            goal=analysis["goal"],
            context=analysis.get("context", {}),
            memory_hints=memory_hints,
        )
        self.event_bus.publish("agents.deliberated", deliberation)

        selected_plan = deliberation["selected_plan"]
        prioritized_tasks = self._prioritize_tasks(analysis.get("generated_tasks", []))
        primary_objective = prioritized_tasks[0]["objective"] if prioritized_tasks else analysis["goal"]

        generated_code = self.code_generation_engine.generate(
            goal=primary_objective,
            context=analysis.get("context", {}),
            selected_plan=selected_plan,
            discussion=deliberation["discussion"],
        )

        plan = {
            "strategy": selected_plan["strategy"],
            "winner_agent": deliberation["winner_agent"],
            "discussion": deliberation["discussion"],
            "scoreboard": deliberation["scoreboard"],
            "agent_plans": deliberation["agent_plans"],
            "generated_tasks": prioritized_tasks,
            "tasks": [
                {
                    "name": "execute-generated-python",
                    "goal": primary_objective,
                    "evidence_count": len(analysis.get("memory_hits", [])),
                    "task_value_score": prioritized_tasks[0]["value_score"] if prioritized_tasks else 0.0,
                    "code": generated_code,
                }
            ],
        }
        self.event_bus.publish("arena.completed", plan)
        return plan

    @staticmethod
    def _prioritize_tasks(tasks: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        filtered = [
            task
            for task in tasks
            if task.get("value_score", 0.0) >= 0.5 and task.get("automation_potential", 0.0) >= 0.45
        ]
        return sorted(
            filtered,
            key=lambda task: (task.get("final_score", task.get("value_score", 0.0)), task.get("confidence", 0.0)),
            reverse=True,
        )

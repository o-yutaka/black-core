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
        candidate_tasks = self._build_candidate_tasks(
            analysis=analysis,
            selected_plan=selected_plan,
            deliberation=deliberation,
        )
        filtered_tasks = self._filter_profitable_tasks(candidate_tasks, analysis)
        conversion_profile = self._build_conversion_profile(analysis)

        plan = {
            "strategy": selected_plan["strategy"],
            "winner_agent": deliberation["winner_agent"],
            "discussion": deliberation["discussion"],
            "scoreboard": deliberation["scoreboard"],
            "agent_plans": deliberation["agent_plans"],
            "tasks": filtered_tasks,
            "conversion_profile": conversion_profile,
        }
        self.event_bus.publish("arena.completed", plan)
        return plan

    def _build_candidate_tasks(
        self,
        analysis: Dict[str, Any],
        selected_plan: Dict[str, Any],
        deliberation: Dict[str, Any],
    ) -> List[Dict[str, Any]]:
        context = analysis.get("context", {})
        api_request = context.get("api_request")

        if isinstance(api_request, dict) and api_request.get("url"):
            base_task = {
                "type": "api",
                "name": "execute-external-api",
                "goal": analysis["goal"],
                "evidence_count": len(analysis.get("memory_hits", [])),
                "method": api_request.get("method", "GET"),
                "url": api_request["url"],
                "query": api_request.get("query", {}),
                "headers": api_request.get("headers", {}),
                "body": api_request.get("body"),
                "timeout_seconds": api_request.get("timeout_seconds", 8),
                "plan_algorithm": selected_plan.get("algorithm", ""),
                "deliberation_points": sum(len(item.get("issues", [])) for item in deliberation.get("discussion", [])),
            }
            return [
                {
                    **base_task,
                    "name": "execute-revenue-api",
                    "profit_priority": 0.92,
                    "conversion_target": "paid_signup",
                },
                {
                    **base_task,
                    "profit_priority": 0.66,
                    "conversion_target": "engagement",
                },
            ]

        generated_code = self.code_generation_engine.generate(
            goal=analysis["goal"],
            context=context,
            selected_plan=selected_plan,
            discussion=deliberation["discussion"],
            conversion_profile=self._build_conversion_profile(analysis),
        )
        base_task = {
            "type": "code",
            "name": "execute-generated-python",
            "goal": analysis["goal"],
            "evidence_count": len(analysis.get("memory_hits", [])),
            "code": generated_code,
        }
        return [
            {
                **base_task,
                "name": "execute-revenue-optimized-python",
                "profit_priority": 0.88,
                "conversion_target": "checkout_completion",
            },
            {
                **base_task,
                "profit_priority": 0.62,
                "conversion_target": "lead_capture",
            },
        ]

    @staticmethod
    def _filter_profitable_tasks(tasks: List[Dict[str, Any]], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        monetization = analysis.get("monetization", {})
        threshold = 0.55 if monetization.get("is_high_value") else 0.7
        profitable = [task for task in tasks if float(task.get("profit_priority", 0.0)) >= threshold]
        return profitable or [max(tasks, key=lambda task: float(task.get("profit_priority", 0.0)))]

    @staticmethod
    def _build_conversion_profile(analysis: Dict[str, Any]) -> Dict[str, Any]:
        monetization = analysis.get("monetization", {})
        conversion_bias = float(monetization.get("conversion_bias", 0.4))
        return {
            "conversion_bias": conversion_bias,
            "message_style": "direct_offer" if conversion_bias >= 0.65 else "value_first",
            "cta_strength": "high" if conversion_bias >= 0.75 else "moderate",
        }

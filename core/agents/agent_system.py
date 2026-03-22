from __future__ import annotations

from typing import Any, Dict

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
        task = self._build_task(analysis=analysis, selected_plan=selected_plan, deliberation=deliberation)

        plan = {
            "strategy": selected_plan["strategy"],
            "winner_agent": deliberation["winner_agent"],
            "discussion": deliberation["discussion"],
            "scoreboard": deliberation["scoreboard"],
            "agent_plans": deliberation["agent_plans"],
            "tasks": [task],
        }
        self.event_bus.publish("arena.completed", plan)
        return plan

    def _build_task(self, analysis: Dict[str, Any], selected_plan: Dict[str, Any], deliberation: Dict[str, Any]) -> Dict[str, Any]:
        context = analysis.get("context", {})
        sns_request = context.get("sns_request")
        if isinstance(sns_request, dict) and str(sns_request.get("platform", "")).lower() == "x":
            return {
                "type": "sns_x",
                "name": "execute-x-operation",
                "goal": analysis["goal"],
                "operation": sns_request.get("operation", "post_and_fetch_metrics"),
                "text": sns_request.get("text", ""),
                "tweet_id": sns_request.get("tweet_id", ""),
                "reply_settings": sns_request.get("reply_settings"),
                "simulation_metrics": sns_request.get("simulation_metrics", {}),
                "plan_algorithm": selected_plan.get("algorithm", ""),
                "deliberation_points": sum(len(item.get("issues", [])) for item in deliberation.get("discussion", [])),
            }

        api_request = context.get("api_request")
        if isinstance(api_request, dict) and api_request.get("url"):
            return {
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

        generated_code = self.code_generation_engine.generate(
            goal=analysis["goal"],
            context=context,
            selected_plan=selected_plan,
            discussion=deliberation["discussion"],
        )
        return {
            "type": "code",
            "name": "execute-generated-python",
            "goal": analysis["goal"],
            "evidence_count": len(analysis.get("memory_hits", [])),
            "code": generated_code,
        }

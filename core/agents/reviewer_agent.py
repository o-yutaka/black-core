from __future__ import annotations

from typing import Any, Dict, List

from core.event_bus import EventBus


class ReviewerAgent:
    """Post-execution reviewer that scores outcome quality and emits improvement directives."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def review(
        self,
        goal: str,
        plan: Dict[str, Any],
        action_result: Dict[str, Any],
        evaluation: Dict[str, Any],
        analysis: Dict[str, Any],
    ) -> Dict[str, Any]:
        strategy = plan.get("strategy", "unknown")
        reward = float(action_result.get("reward", 0.0))
        success = bool(action_result.get("success", False))

        alignment = 1.0 if goal and strategy else 0.4
        reliability = 1.0 if success and not action_result.get("stderr") else 0.5 if success else 0.1
        learning_value = 0.9 if evaluation.get("stored_memory") else 0.3

        score = round((alignment * 0.3) + (reliability * 0.4) + (learning_value * 0.3) + min(0.2, reward * 0.1), 3)

        recommendations: List[str] = []
        if analysis.get("failed_strategies") and strategy in analysis["failed_strategies"]:
            recommendations.append("Selected strategy appears in failed history; switch strategy next cycle.")
        if not success:
            recommendations.append("Execution failed; prioritize deterministic fallback path.")
        if score < 0.75:
            recommendations.append("Increase interview depth and tighten constraints before planning.")
        if not recommendations:
            recommendations.append("Maintain strategy with incremental optimization.")

        review = {
            "goal": goal,
            "strategy": strategy,
            "score": score,
            "success": success,
            "reward": reward,
            "recommendations": recommendations,
            "verdict": "approved" if score >= 0.75 else "revise",
        }
        self.event_bus.publish("reviewer.completed", review)
        return review

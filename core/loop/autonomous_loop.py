from __future__ import annotations

from typing import Any, Dict

from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.performance_comparison_engine import PerformanceComparisonEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.runtime_engine import RuntimeEngine
from executor.runner import ExecutorRunner


class AutonomousLoop:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        goal_engine: GoalGenerationEngine,
        task_intelligence_engine: TaskIntelligenceEngine,
        performance_engine: PerformanceComparisonEngine,
        agent_system: AgentSystem,
        executor_runner: ExecutorRunner,
        event_bus: EventBus,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.goal_engine = goal_engine
        self.task_intelligence_engine = task_intelligence_engine
        self.performance_engine = performance_engine
        self.agent_system = agent_system
        self.executor_runner = executor_runner
        self.event_bus = event_bus

    def run_once(self, state: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.runtime_engine.tick(state)
        goal_pack = self.goal_engine.generate(snapshot)
        analysis = self.task_intelligence_engine.analyze(goal_pack)

        arena_plan = self.agent_system.plan(analysis)
        self.event_bus.publish(
            "evaluation.started",
            {
                "strategy": arena_plan["strategy"],
                "winner_agent": arena_plan.get("winner_agent"),
                "discussion_points": sum(len(item.get("issues", [])) for item in arena_plan.get("discussion", [])),
            },
        )

        action_result = self.executor_runner.run_plan(arena_plan)
        self.event_bus.publish("action.completed", {"plan": arena_plan, "result": action_result})

        performance = self._compare_performance_if_available(action_result=action_result, strategy=arena_plan["strategy"])

        evaluation = self.task_intelligence_engine.evaluate_and_remember(
            goal=goal_pack["goal"],
            strategy=arena_plan["strategy"],
            action_name=arena_plan["tasks"][0]["name"],
            result=action_result,
            performance=performance,
        )

        top_strategy = analysis["top_strategies"][0]["strategy"] if analysis["top_strategies"] else arena_plan["strategy"]
        top_confidence = analysis["top_strategies"][0]["win_rate"] if analysis["top_strategies"] else (0.7 if evaluation["success"] else 0.3)

        if performance:
            evolution = {
                "next_strategy_bias": performance["adjustment"]["next_strategy"],
                "confidence": performance["adjustment"]["confidence"],
                "avoid_strategies": analysis.get("failed_strategies", []),
                "performance_gap": performance["gap"],
            }
        else:
            evolution = {
                "next_strategy_bias": top_strategy,
                "confidence": top_confidence,
                "avoid_strategies": analysis.get("failed_strategies", []),
            }

        self.event_bus.publish("evolution.completed", evolution)
        self.event_bus.publish("design.completed", {"next_strategy": evolution["next_strategy_bias"]})

        summary = {
            "snapshot": snapshot,
            "goal_pack": goal_pack,
            "analysis": analysis,
            "arena_plan": arena_plan,
            "action_result": action_result,
            "performance": performance,
            "evaluation": evaluation,
            "evolution": evolution,
        }
        self.event_bus.publish("loop.completed", summary)
        return summary

    def _compare_performance_if_available(self, action_result: Dict[str, Any], strategy: str) -> Dict[str, Any] | None:
        x_result = action_result.get("x_result")
        if not isinstance(x_result, dict):
            return None

        metrics_payload = x_result.get("metrics", {}).get("data", {}).get("data", {})
        if not metrics_payload:
            return None

        simulation = action_result.get("simulation_metrics", {})
        return self.performance_engine.compare(
            simulation=simulation,
            real_metrics=metrics_payload,
            strategy=strategy,
        )

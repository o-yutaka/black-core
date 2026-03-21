from __future__ import annotations

from typing import Any, Dict

from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.runtime_engine import RuntimeEngine
from executor.runner import ExecutorRunner


class AutonomousLoop:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        goal_engine: GoalGenerationEngine,
        task_intelligence_engine: TaskIntelligenceEngine,
        agent_system: AgentSystem,
        executor_runner: ExecutorRunner,
        event_bus: EventBus,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.goal_engine = goal_engine
        self.task_intelligence_engine = task_intelligence_engine
        self.agent_system = agent_system
        self.executor_runner = executor_runner
        self.event_bus = event_bus

    def run_once(self, state: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.runtime_engine.tick(state)
        goal_pack = self.goal_engine.generate(snapshot)  # ANALYSIS input
        analysis = self.task_intelligence_engine.analyze(goal_pack)  # ANALYSIS

        arena_plan = self.agent_system.plan(analysis)  # ARENA
        self.event_bus.publish("evaluation.started", {"strategy": arena_plan["strategy"]})  # EVALUATION

        action_result = self.executor_runner.run_plan(arena_plan)  # ACTION
        self.event_bus.publish("action.completed", {"plan": arena_plan, "result": action_result})

        evaluation = self.task_intelligence_engine.evaluate_and_remember(
            goal=goal_pack["goal"],
            strategy=arena_plan["strategy"],
            action_name=arena_plan["tasks"][0]["name"],
            result=action_result,
        )  # MEMORY

        evolution = {
            "next_strategy_bias": analysis["top_strategies"][0]["strategy"] if analysis["top_strategies"] else arena_plan["strategy"],
            "confidence": analysis["top_strategies"][0]["win_rate"] if analysis["top_strategies"] else (0.7 if evaluation["success"] else 0.3),
        }
        self.event_bus.publish("evolution.completed", evolution)  # EVOLUTION
        self.event_bus.publish("design.completed", {"next_strategy": evolution["next_strategy_bias"]})  # DESIGN

        summary = {
            "snapshot": snapshot,
            "goal_pack": goal_pack,
            "analysis": analysis,
            "arena_plan": arena_plan,
            "action_result": action_result,
            "evaluation": evaluation,
            "evolution": evolution,
        }
        self.event_bus.publish("loop.completed", summary)  # LOOP
        return summary

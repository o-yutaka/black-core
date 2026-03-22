from __future__ import annotations

from typing import Any, Dict

from core.agents.agent_system import AgentSystem
from core.autonomy.data_ingestion_engine import DataIngestionEngine
from core.autonomy.monetization_strategy_engine import MonetizationStrategyEngine
from core.autonomy.output_channel_engine import OutputChannelEngine
from core.autonomy.persistent_scheduler import PersistentScheduler
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
        data_ingestion_engine: DataIngestionEngine,
        monetization_strategy_engine: MonetizationStrategyEngine,
        persistent_scheduler: PersistentScheduler,
        output_channel_engine: OutputChannelEngine,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.goal_engine = goal_engine
        self.task_intelligence_engine = task_intelligence_engine
        self.agent_system = agent_system
        self.executor_runner = executor_runner
        self.event_bus = event_bus
        self.data_ingestion_engine = data_ingestion_engine
        self.monetization_strategy_engine = monetization_strategy_engine
        self.persistent_scheduler = persistent_scheduler
        self.output_channel_engine = output_channel_engine

    def run_once(self, state: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.runtime_engine.tick(state)

        ingestion_report = self.data_ingestion_engine.ingest(state.get("data_sources"))
        enriched_state = {**state, "external_signals": ingestion_report["signals"]}
        goal_pack = self.goal_engine.generate({**snapshot, "state": enriched_state})
        analysis = self.task_intelligence_engine.analyze(goal_pack)
        monetization_plan = self.monetization_strategy_engine.build_strategy(analysis, ingestion_report)

        arena_plan = self.agent_system.plan({**analysis, "context": {**analysis.get("context", {}), "monetization": monetization_plan}})
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

        evaluation = self.task_intelligence_engine.evaluate_and_remember(
            goal=goal_pack["goal"],
            strategy=arena_plan["strategy"],
            action_name=arena_plan["tasks"][0]["name"],
            result=action_result,
        )

        evolution = {
            "next_strategy_bias": analysis["top_strategies"][0]["strategy"] if analysis["top_strategies"] else arena_plan["strategy"],
            "confidence": analysis["top_strategies"][0]["win_rate"] if analysis["top_strategies"] else (0.7 if evaluation["success"] else 0.3),
            "avoid_strategies": analysis.get("failed_strategies", []),
        }
        self.event_bus.publish("evolution.completed", evolution)
        self.event_bus.publish("design.completed", {"next_strategy": evolution["next_strategy_bias"]})

        output_payload = {
            "cycle": snapshot["cycle"],
            "goal": goal_pack["goal"],
            "monetization": monetization_plan,
            "action_result": action_result,
            "evaluation": evaluation,
        }
        output_reports = self.output_channel_engine.dispatch(state.get("output_channels"), output_payload)

        summary = {
            "snapshot": snapshot,
            "goal_pack": goal_pack,
            "ingestion_report": ingestion_report,
            "analysis": analysis,
            "monetization_plan": monetization_plan,
            "arena_plan": arena_plan,
            "action_result": action_result,
            "evaluation": evaluation,
            "evolution": evolution,
            "output_reports": output_reports,
        }
        self.event_bus.publish("loop.completed", summary)
        return summary

    def run_scheduled_once(self) -> list[dict[str, Any]]:
        return self.persistent_scheduler.run_due_jobs(lambda job: self.run_once(job.get("payload", {})))

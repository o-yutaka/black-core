from __future__ import annotations

from typing import Any, Dict

from core.agents.agent_system import AgentSystem
from core.agents.reviewer_agent import ReviewerAgent
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.interview_engine import InterviewEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.loop.pipeline_controller import PipelineController, PipelineStage
from core.runtime_engine import RuntimeEngine
from executor.runner import ExecutorRunner


class AutonomousLoop:
    def __init__(
        self,
        runtime_engine: RuntimeEngine,
        goal_engine: GoalGenerationEngine,
        task_intelligence_engine: TaskIntelligenceEngine,
        interview_engine: InterviewEngine,
        pipeline_controller: PipelineController,
        reviewer_agent: ReviewerAgent,
        agent_system: AgentSystem,
        executor_runner: ExecutorRunner,
        event_bus: EventBus,
    ) -> None:
        self.runtime_engine = runtime_engine
        self.goal_engine = goal_engine
        self.task_intelligence_engine = task_intelligence_engine
        self.interview_engine = interview_engine
        self.pipeline_controller = pipeline_controller
        self.reviewer_agent = reviewer_agent
        self.agent_system = agent_system
        self.executor_runner = executor_runner
        self.event_bus = event_bus

    def run_once(self, state: Dict[str, Any]) -> Dict[str, Any]:
        snapshot = self.runtime_engine.tick(state)
        goal_pack = self.goal_engine.generate(snapshot)
        analysis = self.task_intelligence_engine.analyze(goal_pack)
        interviewed = self.interview_engine.conduct(analysis)

        self.event_bus.publish("evaluation.started", {"goal": interviewed["goal"], "phase": "planning"})

        pipeline_payload = self.pipeline_controller.run(
            initial_payload={"analysis": interviewed, "goal_pack": goal_pack, "snapshot": snapshot},
            stages=[
                PipelineStage("planning", self._planning_stage),
                PipelineStage("execution", self._execution_stage),
                PipelineStage("memory_evaluation", self._evaluation_stage),
            ],
        )

        arena_plan = pipeline_payload["arena_plan"]
        action_result = pipeline_payload["action_result"]
        evaluation = pipeline_payload["evaluation"]

        review = self.reviewer_agent.review(
            goal=interviewed["goal"],
            plan=arena_plan,
            action_result=action_result,
            evaluation=evaluation,
            analysis=interviewed,
        )

        evolution = {
            "next_strategy_bias": interviewed["top_strategies"][0]["strategy"] if interviewed["top_strategies"] else arena_plan["strategy"],
            "confidence": review["score"],
            "avoid_strategies": interviewed.get("failed_strategies", []),
        }
        self.event_bus.publish("evolution.completed", evolution)
        self.event_bus.publish("design.completed", {"next_strategy": evolution["next_strategy_bias"]})

        summary = {
            "snapshot": snapshot,
            "goal_pack": goal_pack,
            "analysis": analysis,
            "interviewed_analysis": interviewed,
            "arena_plan": arena_plan,
            "action_result": action_result,
            "evaluation": evaluation,
            "review": review,
            "evolution": evolution,
        }
        self.event_bus.publish("loop.completed", summary)
        return summary

    def _planning_stage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        analysis = payload["analysis"]
        arena_plan = self.agent_system.plan(analysis)
        return {"arena_plan": arena_plan}

    def _execution_stage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        arena_plan = payload["arena_plan"]
        action_result = self.executor_runner.run_plan(arena_plan)
        self.event_bus.publish("action.completed", {"plan": arena_plan, "result": action_result})
        return {"action_result": action_result}

    def _evaluation_stage(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        analysis = payload["analysis"]
        arena_plan = payload["arena_plan"]
        action_result = payload["action_result"]

        evaluation = self.task_intelligence_engine.evaluate_and_remember(
            goal=analysis["goal"],
            strategy=arena_plan["strategy"],
            action_name=arena_plan["tasks"][0]["name"],
            result=action_result,
        )
        return {"evaluation": evaluation}

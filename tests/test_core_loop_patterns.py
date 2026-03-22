from __future__ import annotations

from core.agents.agent_system import AgentSystem
from core.agents.reviewer_agent import ReviewerAgent
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.interview_engine import InterviewEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.loop.autonomous_loop import AutonomousLoop
from core.loop.pipeline_controller import PipelineController, PipelineStage
from core.runtime_engine import RuntimeEngine


class FakeMemory:
    def search_memory(self, query: str, top_k: int = 7):
        return [{"strategy": "balanced-execution", "success": True}]

    def top_strategies(self, top_k: int = 5):
        return [{"strategy": "deterministic-optimization", "win_rate": 0.8}]

    def failed_strategies(self, top_k: int = 5):
        return ["random-exploration"]

    def best_practices(self, top_k: int = 3):
        return [{"strategy": "deterministic-optimization", "importance": 1.0}]

    def save_memory(self, **kwargs):
        return {"id": 42, **kwargs}


class FakeExecutorRunner:
    def run_plan(self, plan):
        return {
            "success": True,
            "reward": 1.1,
            "summary": "execution_ok",
            "stdout": "ok",
            "stderr": "",
        }


def test_interview_engine_enriches_analysis_with_constraints_and_risk_register():
    engine = InterviewEngine(event_bus=EventBus())
    analysis = {
        "goal": "Increase reliability",
        "context": {"environment": "production", "target": "reliability", "latency_budget": 4},
        "memory_hits": [],
        "failed_strategies": ["random-exploration"],
    }

    enriched = engine.conduct(analysis)

    assert "interview" in enriched
    assert "constraints" in enriched["interview"]
    assert "risk_register" in enriched["interview"]
    assert "must_preserve_runtime" in enriched["interview"]["constraints"]
    assert "constraints:" in enriched["goal"]


def test_pipeline_controller_executes_stages_in_order_and_merges_payload():
    bus = EventBus()
    controller = PipelineController(event_bus=bus)

    result = controller.run(
        initial_payload={"value": 2},
        stages=[
            PipelineStage("double", lambda p: {"value": p["value"] * 2}),
            PipelineStage("plus_one", lambda p: {"value": p["value"] + 1, "done": True}),
        ],
    )

    assert result["value"] == 5
    assert result["done"] is True


def test_reviewer_agent_scores_result_and_emits_verdict():
    reviewer = ReviewerAgent(event_bus=EventBus())

    review = reviewer.review(
        goal="Increase reliability",
        plan={"strategy": "deterministic-optimization"},
        action_result={"success": True, "reward": 1.0, "stderr": ""},
        evaluation={"stored_memory": {"id": 1}},
        analysis={"failed_strategies": ["random-exploration"]},
    )

    assert review["verdict"] == "approved"
    assert review["score"] >= 0.75


def test_autonomous_loop_integrates_interview_pipeline_and_reviewer_layers():
    event_bus = EventBus()
    runtime_engine = RuntimeEngine(event_bus=event_bus)
    goal_engine = GoalGenerationEngine(event_bus=event_bus)
    task_intelligence_engine = TaskIntelligenceEngine(event_bus=event_bus, memory=FakeMemory())
    interview_engine = InterviewEngine(event_bus=event_bus)
    pipeline_controller = PipelineController(event_bus=event_bus)
    reviewer_agent = ReviewerAgent(event_bus=event_bus)
    agent_system = AgentSystem(event_bus=event_bus)
    executor_runner = FakeExecutorRunner()

    loop = AutonomousLoop(
        runtime_engine=runtime_engine,
        goal_engine=goal_engine,
        task_intelligence_engine=task_intelligence_engine,
        interview_engine=interview_engine,
        pipeline_controller=pipeline_controller,
        reviewer_agent=reviewer_agent,
        agent_system=agent_system,
        executor_runner=executor_runner,
        event_bus=event_bus,
    )

    runtime_engine.start()
    summary = loop.run_once({"goal": "Increase reliability", "environment": "production", "target": "reliability"})

    assert "interviewed_analysis" in summary
    assert "review" in summary
    assert summary["review"]["verdict"] in {"approved", "revise"}
    assert summary["evolution"]["confidence"] == summary["review"]["score"]

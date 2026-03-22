from __future__ import annotations

from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.performance_comparison_engine import PerformanceComparisonEngine
from executor.runner import ExecutorRunner


def test_agent_system_builds_x_sns_task():
    system = AgentSystem(event_bus=EventBus())

    analysis = {
        "goal": "Ship campaign to X and measure real engagement",
        "context": {
            "sns_request": {
                "platform": "x",
                "operation": "post_and_fetch_metrics",
                "text": "BLACK ORIGIN now executes real-world X publishing.",
                "simulation_metrics": {"likes": 20, "reposts": 4, "replies": 3, "quotes": 1, "impressions": 1000},
            }
        },
        "memory_hits": [],
        "top_strategies": [{"strategy": "deterministic-optimization", "win_rate": 0.9}],
        "failed_strategies": [],
    }

    plan = system.plan(analysis)
    task = plan["tasks"][0]

    assert task["type"] == "sns_x"
    assert task["operation"] == "post_and_fetch_metrics"
    assert task["simulation_metrics"]["likes"] == 20


def test_performance_engine_compares_simulation_to_real_metrics():
    engine = PerformanceComparisonEngine(event_bus=EventBus())

    result = engine.compare(
        simulation={"likes": 20, "reposts": 3, "replies": 2, "quotes": 1, "impressions": 1200},
        real_metrics={
            "public_metrics": {
                "like_count": 15,
                "retweet_count": 2,
                "reply_count": 1,
                "quote_count": 0,
                "impression_count": 600,
            }
        },
        strategy="adaptive-hybrid-search",
    )

    assert result["gap"]["simulated_engagement"] > result["gap"]["real_engagement"]
    assert result["adjustment"]["next_strategy"].endswith(":recalibrate")


def test_executor_runner_executes_x_task_with_live_result_shape():
    runner = ExecutorRunner(event_bus=EventBus(), timeout_seconds=2)

    def _fake_execute(task):
        return {
            "success": True,
            "summary": "x_posted_and_measured",
            "post": {"data": {"data": {"id": "123"}}},
            "metrics": {
                "data": {
                    "data": {
                        "id": "123",
                        "public_metrics": {
                            "like_count": 5,
                            "retweet_count": 2,
                            "reply_count": 1,
                            "quote_count": 1,
                        },
                    }
                }
            },
        }

    runner.x_executor.execute = _fake_execute
    plan = {
        "strategy": "social-scale",
        "tasks": [
            {
                "type": "sns_x",
                "name": "execute-x-operation",
                "operation": "post_and_fetch_metrics",
                "text": "Autonomous execution online.",
                "simulation_metrics": {"likes": 8},
            }
        ],
    }

    result = runner.run_plan(plan)
    assert result["success"] is True
    assert result["x_result"]["summary"] == "x_posted_and_measured"
    assert result["reward"] > 0

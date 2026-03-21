from core.event_bus import EventBus
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine


class FakeMemory:
    def search_memory(self, query: str, top_k: int = 5):
        return [
            {"strategy": "aggressive-profit", "success": True},
            {"strategy": "aggressive-profit", "success": True},
            {"strategy": "aggressive-profit", "success": False},
            {"strategy": "safe-mode", "success": False},
        ]

    def top_strategies(self, top_k: int = 3):
        return [{"strategy": "aggressive-profit", "win_rate": 0.9}]

    def failed_strategies(self, top_k: int = 5):
        return ["aggressive-profit", "safe-mode"]

    def best_practices(self, top_k: int = 3):
        return [{"strategy": "aggressive-profit", "importance": 1.0}]

    def save_memory(self, **kwargs):
        return {"id": 1, **kwargs}


def test_recommends_successful_strategy_and_records_memory():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())

    analysis = engine.analyze({"goal": "maximize reward", "context": {"production": True, "latency_budget": 4}})
    assert analysis["recommended_strategy"] == "aggressive-profit"
    assert analysis["generated_tasks"]
    assert all(task["value_score"] >= 0.5 for task in analysis["generated_tasks"])
    assert all(task["kind"] != "meta" for task in analysis["generated_tasks"])
    assert all(task["strategy_success_rate"] >= 0.55 for task in analysis["generated_tasks"])
    assert all(task["final_score"] >= task["value_score"] * 0.75 for task in analysis["generated_tasks"])

    evaluation = engine.evaluate_and_remember(
        goal="maximize reward",
        strategy=analysis["recommended_strategy"],
        action_name="execute-primary-strategy",
        result={"success": True, "reward": 1.2, "summary": "won"},
    )
    assert evaluation["success"] is True
    assert evaluation["reward"] == 1.2
    assert evaluation["stored_memory"]["strategy"] == "aggressive-profit"


def test_failed_flagged_strategy_is_kept_when_success_rate_is_high():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())
    analysis = engine.analyze({"goal": "improve throughput", "context": {"production": True, "urgent": True}})

    aggressive = next(item for item in analysis["strategy_health"] if item["strategy"] == "aggressive-profit")
    assert aggressive["failed_flag"] is True
    assert aggressive["success_rate"] >= 0.55
    assert all(task["strategy"] == "aggressive-profit" for task in analysis["generated_tasks"])

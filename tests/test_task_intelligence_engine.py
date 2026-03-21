from core.event_bus import EventBus
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine


class FakeMemory:
    def search_memory(self, query: str, top_k: int = 5):
        return [
            {"strategy": "aggressive-profit", "success": True},
            {"strategy": "safe-mode", "success": False},
        ]

    def top_strategies(self, top_k: int = 3):
        return [{"strategy": "aggressive-profit", "win_rate": 0.9}]

    def save_memory(self, **kwargs):
        return {"id": 1, **kwargs}


def test_recommends_successful_strategy_and_records_memory():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())

    analysis = engine.analyze({"goal": "maximize reward", "context": {}})
    assert analysis["recommended_strategy"] == "aggressive-profit"

    evaluation = engine.evaluate_and_remember(
        goal="maximize reward",
        strategy=analysis["recommended_strategy"],
        action_name="execute-primary-strategy",
        result={"success": True, "reward": 1.2, "summary": "won"},
    )
    assert evaluation["success"] is True
    assert evaluation["reward"] == 1.2
    assert evaluation["stored_memory"]["strategy"] == "aggressive-profit"

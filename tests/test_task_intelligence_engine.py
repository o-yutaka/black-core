from core.event_bus import EventBus
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine


class FakeMemory:
    def __init__(self):
        self.saved = None

    def search_memory(self, query: str, top_k: int = 5):
        return [
            {"strategy": "aggressive-profit", "success": True},
            {"strategy": "safe-mode", "success": False},
        ]

    def top_strategies(self, top_k: int = 3):
        return [{"strategy": "aggressive-profit", "win_rate": 0.9}]

    def failed_strategies(self, top_k: int = 5):
        return ["safe-mode"]

    def best_practices(self, top_k: int = 3):
        return [{"strategy": "aggressive-profit", "importance": 1.0}]

    def save_memory(self, **kwargs):
        self.saved = kwargs
        return {"id": 1, **kwargs}


def test_recommends_successful_strategy_and_records_memory():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())

    analysis = engine.analyze({"goal": "maximize reward", "context": {}})
    assert analysis["recommended_strategy"] == "aggressive-profit"
    assert analysis["failed_strategies"] == ["safe-mode"]

    evaluation = engine.evaluate_and_remember(
        goal="maximize reward",
        strategy=analysis["recommended_strategy"],
        action_name="execute-primary-strategy",
        result={"success": True, "reward": 1.2, "summary": "won"},
    )
    assert evaluation["success"] is True
    assert evaluation["reward"] == 1.2
    assert evaluation["stored_memory"]["strategy"] == "aggressive-profit"


def test_records_api_result_in_memory_context_and_summary():
    memory = FakeMemory()
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=memory)

    engine.evaluate_and_remember(
        goal="load weather",
        strategy="external-api",
        action_name="execute-external-api",
        result={
            "success": True,
            "reward": 1.0,
            "summary": "api_call_succeeded",
            "api_result": {
                "method": "GET",
                "url": "https://example.org/weather",
                "status_code": 200,
                "body": {"temp": 71},
            },
        },
    )

    assert "Status=200" in memory.saved["text"]
    assert memory.saved["context"]["api_result"]["body"]["temp"] == 71


def test_records_x_and_performance_data_in_memory_context():
    memory = FakeMemory()
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=memory)

    engine.evaluate_and_remember(
        goal="grow social engagement",
        strategy="social-scale",
        action_name="execute-x-operation",
        result={
            "success": True,
            "reward": 1.1,
            "summary": "x_posted_and_measured",
            "x_result": {
                "post": {"data": {"data": {"id": "991"}}},
                "metrics": {
                    "data": {
                        "data": {
                            "public_metrics": {"like_count": 41}
                        }
                    }
                },
            },
        },
        performance={"gap": {"delta": -4.0, "ratio": 0.8}},
    )

    assert "XTweetID=991" in memory.saved["text"]
    assert memory.saved["context"]["performance"]["gap"]["ratio"] == 0.8

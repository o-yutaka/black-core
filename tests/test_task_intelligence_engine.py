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


def test_prefers_external_api_strategy_when_knowledge_router_has_api_hits_and_no_history():
    class EmptyMemory(FakeMemory):
        def search_memory(self, query: str, top_k: int = 5):
            return []

        def top_strategies(self, top_k: int = 3):
            return []

    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=EmptyMemory())

    analysis = engine.analyze(
        {
            "goal": "fetch weather",
            "context": {},
            "knowledge": {
                "api_hits": [{"request": {"url": "https://example.org/weather"}}],
                "local_documents": [],
            },
        }
    )

    assert analysis["recommended_strategy"] == "external-api"
    assert len(analysis["api_hits"]) == 1

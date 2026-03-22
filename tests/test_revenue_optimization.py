from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine


class FakeMemory:
    def search_memory(self, query: str, top_k: int = 5):
        return [{"strategy": "profit-max", "success": True}]

    def top_strategies(self, top_k: int = 3):
        return [{"strategy": "profit-max", "win_rate": 0.91}]

    def failed_strategies(self, top_k: int = 5):
        return ["low-margin"]

    def best_practices(self, top_k: int = 3):
        return [{"strategy": "high-conversion-funnel", "importance": 0.9}]

    def save_memory(self, **kwargs):
        return {"id": 1, **kwargs}


def test_monetization_score_is_attached_to_analysis():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())
    analysis = engine.analyze(
        {
            "goal": "Increase conversion and profit from premium upgrades",
            "context": {"revenue_target": 40, "channel": "paid_search"},
        }
    )

    assert analysis["monetization"]["profit_score"] > 0.6
    assert analysis["monetization"]["conversion_bias"] > 0.6
    assert analysis["monetization"]["is_high_value"] is True


def test_agent_system_filters_tasks_to_profitable_candidates():
    system = AgentSystem(event_bus=EventBus())
    plan = system.plan(
        {
            "goal": "Increase conversion and revenue",
            "context": {"segment": "enterprise"},
            "memory_hits": [],
            "top_strategies": [{"strategy": "deterministic-optimization", "win_rate": 0.8}],
            "failed_strategies": [],
            "monetization": {"is_high_value": True, "conversion_bias": 0.82},
        }
    )

    assert plan["tasks"]
    assert all(task["profit_priority"] >= 0.55 for task in plan["tasks"])
    assert plan["conversion_profile"]["cta_strength"] == "high"

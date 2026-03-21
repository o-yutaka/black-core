from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus


def test_agent_system_runs_multi_agent_deliberation_and_generates_executable_code():
    system = AgentSystem(event_bus=EventBus())

    analysis = {
        "goal": "Improve reliability for production workflows",
        "context": {"environment": "production", "target": "reliability", "latency_budget": 4},
        "memory_hits": [],
        "top_strategies": [{"strategy": "deterministic-optimization", "win_rate": 0.8}],
        "failed_strategies": ["random-exploration"],
    }

    plan = system.plan(analysis)

    assert plan["winner_agent"] in {"logic_agent", "creative_agent", "critical_agent"}
    assert len(plan["agent_plans"]) == 3
    assert len(plan["discussion"]) == 3
    assert "print(json.dumps(result" in plan["tasks"][0]["code"]

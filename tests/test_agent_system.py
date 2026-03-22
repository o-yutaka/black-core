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
    assert plan["tasks"][0]["type"] == "code"
    assert "print(json.dumps(result" in plan["tasks"][0]["code"]
    assert plan["tasks"][0]["execution_target"] == "local"


def test_agent_system_builds_api_task_when_context_requests_external_call():
    system = AgentSystem(event_bus=EventBus())

    analysis = {
        "goal": "Collect weather from external service",
        "context": {
            "api_request": {
                "method": "GET",
                "url": "https://example.org/weather",
                "query": {"city": "NewYork"},
                "headers": {"Accept": "application/json"},
            }
        },
        "memory_hits": [],
        "top_strategies": [{"strategy": "deterministic-optimization", "win_rate": 0.7}],
        "failed_strategies": [],
    }

    plan = system.plan(analysis)
    task = plan["tasks"][0]

    assert task["type"] == "api"
    assert task["name"] == "execute-external-api"
    assert task["url"] == "https://example.org/weather"
    assert task["query"]["city"] == "NewYork"


def test_agent_system_builds_cloud_execution_code_task_from_context():
    system = AgentSystem(event_bus=EventBus())

    analysis = {
        "goal": "Execute optimizer remotely",
        "context": {
            "cloud_execution": {
                "url": "https://executor.black-origin.example/run",
                "headers": {"X-Cluster": "alpha"},
            },
            "max_code_iterations": 3,
            "target": "throughput",
        },
        "memory_hits": [],
        "top_strategies": [{"strategy": "cloud-optimization", "win_rate": 0.8}],
        "failed_strategies": ["legacy-local"],
    }

    plan = system.plan(analysis)
    task = plan["tasks"][0]

    assert task["type"] == "code"
    assert task["execution_target"] == "cloud"
    assert task["cloud_execution"]["url"].startswith("https://executor")
    assert task["max_iterations"] == 3

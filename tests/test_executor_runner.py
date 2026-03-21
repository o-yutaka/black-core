from core.event_bus import EventBus
from executor.runner import ExecutorRunner


def test_executor_runner_executes_plan_code():
    runner = ExecutorRunner(event_bus=EventBus(), timeout_seconds=2)
    plan = {
        "strategy": "balanced",
        "tasks": [{"name": "execute-generated-python", "code": "print(2 + 2)"}],
    }

    result = runner.run_plan(plan)

    assert result["success"] is True
    assert result["stdout"].strip() == "4"

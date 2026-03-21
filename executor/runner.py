from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus
from executor.code_runner import CodeRunner, CodeSafetyError


class ExecutorRunner:
    """Bridges core plan objects and concrete python code execution."""

    def __init__(self, event_bus: EventBus, timeout_seconds: int = 5) -> None:
        self.event_bus = event_bus
        self.code_runner = CodeRunner(timeout_seconds=timeout_seconds)

    def run_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        task = plan["tasks"][0]
        code = task.get("code", "")
        if not code:
            result = {
                "success": False,
                "stdout": "",
                "stderr": "No code in plan",
                "return_code": 2,
                "timed_out": False,
                "summary": "execution_failed",
                "reward": -0.5,
            }
            self.event_bus.publish("executor.completed", {"plan": plan, "result": result})
            return result

        try:
            result = self.code_runner.run(code).as_dict()
        except CodeSafetyError as error:
            result = {
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "return_code": 126,
                "timed_out": False,
                "summary": "execution_blocked",
                "reward": -0.7,
            }

        self.event_bus.publish("executor.completed", {"plan": plan, "result": result})
        return result

from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus
from executor.api_executor import APIExecutionError, APIExecutor
from executor.code_runner import CodeRunner, CodeSafetyError
from executor.sns_executor import SNSExecutor


class ExecutorRunner:
    """Bridges core plan objects and concrete action execution subsystems."""

    def __init__(self, event_bus: EventBus, timeout_seconds: int = 5) -> None:
        self.event_bus = event_bus
        self.code_runner = CodeRunner(timeout_seconds=timeout_seconds)
        self.api_executor = APIExecutor()
        self.sns_executor = SNSExecutor()

    def run_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        task = plan["tasks"][0]
        task_type = str(task.get("type", "code")).lower()

        if task_type == "api":
            result = self._run_api_task(task)
        elif task_type == "sns_campaign":
            result = self._run_sns_task(task)
        else:
            result = self._run_code_task(task)

        self.event_bus.publish("executor.completed", {"plan": plan, "result": result})
        return result

    def _run_code_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        code = task.get("code", "")
        if not code:
            return {
                "success": False,
                "stdout": "",
                "stderr": "No code in plan",
                "return_code": 2,
                "timed_out": False,
                "summary": "execution_failed",
                "reward": -0.5,
            }

        try:
            return self.code_runner.run(code).as_dict()
        except CodeSafetyError as error:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "return_code": 126,
                "timed_out": False,
                "summary": "execution_blocked",
                "reward": -0.7,
            }

    def _run_api_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.event_bus.publish("api.execution.started", {"task": task})
        try:
            api_result = self.api_executor.execute(task)
            result = {
                "success": api_result["success"],
                "stdout": "",
                "stderr": "",
                "return_code": 0 if api_result["success"] else 1,
                "timed_out": False,
                "summary": api_result["summary"],
                "reward": 1.0 if api_result["success"] else -0.4,
                "api_result": api_result,
            }
        except APIExecutionError as error:
            result = {
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "return_code": 3,
                "timed_out": False,
                "summary": "api_task_invalid",
                "reward": -0.6,
                "api_result": None,
            }

        self.event_bus.publish("api.execution.completed", {"task": task, "result": result})
        return result

    def _run_sns_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.event_bus.publish("sns.execution.started", {"task": task})
        result = self.sns_executor.execute_campaign(task)
        self.event_bus.publish("sns.execution.completed", {"task": task, "result": result})
        return result

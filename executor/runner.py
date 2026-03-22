from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus
from executor.api_executor import APIExecutionError, APIExecutor
from executor.code_runner import CodeRunner, CodeSafetyError
from executor.x_executor import XExecutionError, XExecutor


class ExecutorRunner:
    """Bridges core plan objects and concrete action execution subsystems."""

    def __init__(self, event_bus: EventBus, timeout_seconds: int = 5) -> None:
        self.event_bus = event_bus
        self.code_runner = CodeRunner(timeout_seconds=timeout_seconds)
        self.api_executor = APIExecutor()
        self.x_executor = XExecutor()

    def run_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        task = plan["tasks"][0]
        task_type = str(task.get("type", "code")).lower()

        if task_type == "api":
            result = self._run_api_task(task)
        elif task_type == "sns_x":
            result = self._run_x_task(task)
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

    def _run_x_task(self, task: Dict[str, Any]) -> Dict[str, Any]:
        self.event_bus.publish("sns.x.execution.started", {"task": task})
        try:
            x_result = self.x_executor.execute(task)
            metrics = x_result.get("metrics", {}).get("data", {}).get("data", {}).get("public_metrics", {})
            engagement = (
                float(metrics.get("like_count", 0.0))
                + 2.0 * float(metrics.get("retweet_count", 0.0))
                + 1.5 * float(metrics.get("reply_count", 0.0))
                + 2.5 * float(metrics.get("quote_count", 0.0))
            )
            reward = max(0.2, min(2.0, 0.5 + (engagement / 100.0)))
            result = {
                "success": x_result["success"],
                "stdout": "",
                "stderr": "",
                "return_code": 0,
                "timed_out": False,
                "summary": x_result["summary"],
                "reward": reward,
                "x_result": x_result,
                "simulation_metrics": task.get("simulation_metrics", {}),
            }
        except XExecutionError as error:
            result = {
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "return_code": 4,
                "timed_out": False,
                "summary": "sns_x_failed",
                "reward": -0.5,
                "x_result": None,
                "simulation_metrics": task.get("simulation_metrics", {}),
            }

        self.event_bus.publish("sns.x.execution.completed", {"task": task, "result": result})
        return result

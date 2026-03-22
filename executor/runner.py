from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus
from executor.api_executor import APIExecutionError, APIExecutor
from executor.cloud_execution_layer import CloudExecutionError, CloudExecutionLayer
from executor.code_generation_engine import CodeGenerationEngine
from executor.code_runner import CodeRunner, CodeSafetyError


class ExecutorRunner:
    """Bridges core plan objects and concrete action execution subsystems."""

    def __init__(self, event_bus: EventBus, timeout_seconds: int = 5) -> None:
        self.event_bus = event_bus
        self.code_runner = CodeRunner(timeout_seconds=timeout_seconds)
        self.api_executor = APIExecutor()
        self.cloud_execution_layer = CloudExecutionLayer(api_executor=self.api_executor)
        self.code_generation_engine = CodeGenerationEngine()

    def run_plan(self, plan: Dict[str, Any]) -> Dict[str, Any]:
        task = plan["tasks"][0]
        task_type = str(task.get("type", "code")).lower()

        if task_type == "api":
            result = self._run_api_task(task)
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

        max_iterations = max(1, int(task.get("max_iterations", 1)))
        attempt = 1
        latest = self._execute_code(code=code, task={**task, "attempt": attempt})
        attempts = [{"attempt": attempt, "result": latest, "code": code}]

        while not latest.get("success") and attempt < max_iterations:
            attempt += 1
            refined_code = self.code_generation_engine.refine(
                goal=str(task.get("goal", "")),
                context=task.get("context", {}),
                selected_plan=task.get("selected_plan", {"strategy": task.get("plan_strategy", "balanced-execution")}),
                discussion=task.get("discussion", []),
                previous_result=latest,
                attempt=attempt,
            )
            self.event_bus.publish(
                "execution.iteration.refined",
                {
                    "task_name": task.get("name"),
                    "goal": task.get("goal"),
                    "attempt": attempt,
                    "previous_summary": latest.get("summary"),
                },
            )

            latest = self._execute_code(code=refined_code, task={**task, "attempt": attempt})
            attempts.append({"attempt": attempt, "result": latest, "code": refined_code})

        final_result = {
            **latest,
            "attempt_count": len(attempts),
            "attempts": [
                {
                    "attempt": item["attempt"],
                    "success": bool(item["result"].get("success")),
                    "summary": item["result"].get("summary"),
                    "return_code": item["result"].get("return_code"),
                    "execution_mode": item["result"].get("execution_mode", "local"),
                }
                for item in attempts
            ],
        }
        return final_result

    def _execute_code(self, code: str, task: Dict[str, Any]) -> Dict[str, Any]:
        execution_target = str(task.get("execution_target", "local")).lower()
        if execution_target == "cloud":
            self.event_bus.publish("cloud.execution.started", {"task": task})
            try:
                result = self.cloud_execution_layer.execute_code(code=code, task=task)
            except CloudExecutionError as error:
                result = {
                    "success": False,
                    "stdout": "",
                    "stderr": str(error),
                    "return_code": 125,
                    "timed_out": False,
                    "summary": "cloud_execution_unavailable",
                    "reward": -0.6,
                    "execution_mode": "cloud",
                }
            self.event_bus.publish("cloud.execution.completed", {"task": task, "result": result})
            return result

        try:
            result = self.code_runner.run(code).as_dict()
            result["execution_mode"] = "local"
            return result
        except CodeSafetyError as error:
            return {
                "success": False,
                "stdout": "",
                "stderr": str(error),
                "return_code": 126,
                "timed_out": False,
                "summary": "execution_blocked",
                "reward": -0.7,
                "execution_mode": "local",
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

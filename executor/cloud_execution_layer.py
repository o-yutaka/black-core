from __future__ import annotations

import json
from typing import Any, Dict

from executor.api_executor import APIExecutionError, APIExecutor


class CloudExecutionError(RuntimeError):
    """Raised when cloud execution cannot return a valid result payload."""


class CloudExecutionLayer:
    """Executes generated code through a remote cloud execution API."""

    def __init__(self, api_executor: APIExecutor | None = None) -> None:
        self.api_executor = api_executor or APIExecutor()

    def execute_code(self, code: str, task: Dict[str, Any]) -> Dict[str, Any]:
        cloud_cfg = task.get("cloud_execution") or {}
        endpoint = str(cloud_cfg.get("url", "")).strip()
        if not endpoint:
            raise CloudExecutionError("Cloud execution endpoint is missing")

        headers = {str(k): str(v) for k, v in (cloud_cfg.get("headers") or {}).items()}
        token = cloud_cfg.get("token")
        if token and "Authorization" not in headers:
            headers["Authorization"] = f"Bearer {token}"

        timeout = float(cloud_cfg.get("timeout_seconds", task.get("timeout_seconds", 8)))
        payload = {
            "language": "python",
            "code": code,
            "goal": task.get("goal"),
            "attempt": int(task.get("attempt", 1)),
            "metadata": {
                "task_name": task.get("name"),
                "strategy": task.get("plan_strategy"),
            },
        }

        request_task = {
            "method": "POST",
            "url": endpoint,
            "headers": headers,
            "timeout_seconds": timeout,
            "body": payload,
        }

        try:
            api_result = self.api_executor.execute(request_task)
        except APIExecutionError as error:
            raise CloudExecutionError(str(error)) from error

        parsed = self._coerce_result(api_result)
        parsed["api_result"] = api_result
        return parsed

    def _coerce_result(self, api_result: Dict[str, Any]) -> Dict[str, Any]:
        body = api_result.get("body")
        if isinstance(body, str):
            try:
                body = json.loads(body)
            except json.JSONDecodeError:
                body = {"stdout": body}

        if not isinstance(body, dict):
            body = {}

        return_code = int(body.get("return_code", 0 if api_result.get("success") else 1))
        timed_out = bool(body.get("timed_out", False))
        stdout = str(body.get("stdout", ""))
        stderr = str(body.get("stderr", body.get("error", "")))
        success = bool(body.get("success", api_result.get("success", False))) and return_code == 0 and not timed_out
        summary = str(body.get("summary", "cloud_execution_success" if success else "cloud_execution_failed"))

        return {
            "success": success,
            "stdout": stdout,
            "stderr": stderr,
            "return_code": return_code,
            "timed_out": timed_out,
            "summary": summary,
            "reward": 1.0 if success else -0.5,
            "execution_mode": "cloud",
        }

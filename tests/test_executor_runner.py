from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from core.event_bus import EventBus
from executor.runner import ExecutorRunner


class _APIHandler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        body = json.dumps({"ok": True, "path": self.path}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


class _CloudExecHandler(BaseHTTPRequestHandler):
    attempts = 0

    def do_POST(self):  # noqa: N802
        content_length = int(self.headers.get("Content-Length", "0"))
        payload = json.loads(self.rfile.read(content_length).decode("utf-8"))
        _CloudExecHandler.attempts += 1

        if _CloudExecHandler.attempts == 1:
            response = {
                "success": False,
                "stdout": "",
                "stderr": "simulated first failure",
                "return_code": 1,
                "summary": "execution_failed",
                "timed_out": False,
            }
        else:
            response = {
                "success": True,
                "stdout": json.dumps({"attempt": payload.get("attempt", 2)}),
                "stderr": "",
                "return_code": 0,
                "summary": "execution_success",
                "timed_out": False,
            }

        raw = json.dumps(response).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(raw)))
        self.end_headers()
        self.wfile.write(raw)

    def log_message(self, format, *args):  # noqa: A003
        return


def test_executor_runner_executes_plan_code():
    runner = ExecutorRunner(event_bus=EventBus(), timeout_seconds=2)
    plan = {
        "strategy": "balanced",
        "tasks": [{"name": "execute-generated-python", "code": "print(2 + 2)"}],
    }

    result = runner.run_plan(plan)

    assert result["success"] is True
    assert result["stdout"].strip() == "4"


def test_executor_runner_executes_api_task():
    server = HTTPServer(("127.0.0.1", 0), _APIHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        runner = ExecutorRunner(event_bus=EventBus(), timeout_seconds=2)
        plan = {
            "strategy": "external-api",
            "tasks": [
                {
                    "type": "api",
                    "name": "execute-external-api",
                    "method": "GET",
                    "url": f"http://127.0.0.1:{server.server_port}/health",
                    "query": {"source": "test"},
                }
            ],
        }

        result = runner.run_plan(plan)

        assert result["success"] is True
        assert result["api_result"]["status_code"] == 200
        assert result["api_result"]["body"]["ok"] is True
        assert "source=test" in result["api_result"]["body"]["path"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_executor_runner_cloud_execution_and_iterative_refinement():
    _CloudExecHandler.attempts = 0
    server = HTTPServer(("127.0.0.1", 0), _CloudExecHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        runner = ExecutorRunner(event_bus=EventBus(), timeout_seconds=2)
        plan = {
            "strategy": "cloud-optimization",
            "tasks": [
                {
                    "type": "code",
                    "name": "execute-generated-python",
                    "goal": "raise execution reliability",
                    "context": {"latency_budget": 4},
                    "selected_plan": {"strategy": "cloud-optimization", "algorithm": "weighted-priority-selection"},
                    "discussion": [{"issues": ["first_pass"]}],
                    "execution_target": "cloud",
                    "max_iterations": 2,
                    "cloud_execution": {"url": f"http://127.0.0.1:{server.server_port}/execute"},
                    "code": "print('initial-attempt')",
                }
            ],
        }

        result = runner.run_plan(plan)

        assert result["success"] is True
        assert result["attempt_count"] == 2
        assert all(item["execution_mode"] == "cloud" for item in result["attempts"])
        assert _CloudExecHandler.attempts == 2
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

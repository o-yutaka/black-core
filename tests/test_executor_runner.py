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

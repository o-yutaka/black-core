from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from executor.api_executor import APIExecutor


class _Handler(BaseHTTPRequestHandler):
    def do_GET(self):  # noqa: N802
        payload = {"path": self.path, "method": "GET"}
        body = json.dumps(payload).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def log_message(self, format, *args):  # noqa: A003
        return


def test_api_executor_executes_get_with_query():
    server = HTTPServer(("127.0.0.1", 0), _Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        executor = APIExecutor()
        result = executor.execute(
            {
                "method": "GET",
                "url": f"http://127.0.0.1:{server.server_port}/ping",
                "query": {"q": "black-origin"},
            }
        )

        assert result["success"] is True
        assert result["status_code"] == 200
        assert result["body"]["method"] == "GET"
        assert "q=black-origin" in result["body"]["path"]
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

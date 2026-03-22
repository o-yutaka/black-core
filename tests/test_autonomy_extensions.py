from __future__ import annotations

import json
import threading
from http.server import BaseHTTPRequestHandler, HTTPServer

from api.black import build_black_origin
from core.autonomy.output_channel_engine import OutputChannelEngine


class _JSONHandler(BaseHTTPRequestHandler):
    received = []

    def do_GET(self):  # noqa: N802
        body = json.dumps({"ok": True, "path": self.path, "trend": "ai-agents"}).encode("utf-8")
        self.send_response(200)
        self.send_header("Content-Type", "application/json")
        self.send_header("Content-Length", str(len(body)))
        self.end_headers()
        self.wfile.write(body)

    def do_POST(self):  # noqa: N802
        size = int(self.headers.get("Content-Length", "0"))
        _JSONHandler.received.append(json.loads(self.rfile.read(size).decode("utf-8")))
        self.send_response(200)
        self.end_headers()

    def log_message(self, format, *args):  # noqa: A003
        return


def test_autonomous_loop_ingests_builds_monetization_and_dispatches_outputs(tmp_path):
    server = HTTPServer(("127.0.0.1", 0), _JSONHandler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()

    try:
        system = build_black_origin(memory_dir=str(tmp_path / "mem"))
        runtime = system["runtime_engine"]
        loop = system["autonomous_loop"]

        runtime.start()
        summary = loop.run_once(
            {
                "goal": "Generate autonomous revenue",
                "data_sources": [
                    {"name": "social-pulse", "type": "social", "url": f"http://127.0.0.1:{server.server_port}/social"},
                    {"name": "market-api", "type": "api", "url": f"http://127.0.0.1:{server.server_port}/market"},
                ],
                "output_channels": [
                    {"type": "webhook", "url": f"http://127.0.0.1:{server.server_port}/webhook"},
                    {"type": "api"},
                    {"type": "file", "path": str(tmp_path / "feed.jsonl")},
                ],
            }
        )
        runtime.stop("test-complete")

        assert summary["ingestion_report"]["signal_count"] == 2
        assert summary["monetization_plan"]["projected_revenue"] > 0
        assert summary["output_reports"][0]["success"] is True
        assert len(_JSONHandler.received) == 1
        assert _JSONHandler.received[0]["goal"] == "Generate autonomous revenue"
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)


def test_persistent_scheduler_runs_due_job(tmp_path):
    system = build_black_origin(memory_dir=str(tmp_path / "mem"))
    runtime = system["runtime_engine"]
    scheduler = system["persistent_scheduler"]
    loop = system["autonomous_loop"]

    runtime.start()
    scheduler.register_job(
        name="fast-job",
        interval_seconds=1,
        payload={"goal": "Capture short interval opportunity", "output_channels": [{"type": "api"}]},
    )

    import sqlite3

    with sqlite3.connect(tmp_path / "mem" / "scheduler.db") as conn:
        conn.execute("UPDATE scheduled_jobs SET next_run_at = '2000-01-01T00:00:00+00:00' WHERE name = 'fast-job'")
        conn.commit()

    results = loop.run_scheduled_once()
    runtime.stop("scheduled-test-complete")

    assert len(results) == 1
    assert results[0]["result"]["goal_pack"]["goal"] == "Capture short interval opportunity"


def test_output_channel_api_server_exposes_latest_payload():
    engine = OutputChannelEngine(event_bus=build_black_origin()["event_bus"])
    server_pack = engine.start_api_server(port=0)
    server = server_pack["server"]
    thread = server_pack["thread"]

    try:
        engine.dispatch([{"type": "api"}], {"goal": "serve-latest", "success": True})
        from urllib import request

        with request.urlopen(f"http://127.0.0.1:{server.server_port}/latest", timeout=2) as response:  # noqa: S310
            data = json.loads(response.read().decode("utf-8"))

        assert data["goal"] == "serve-latest"
        assert data["success"] is True
    finally:
        server.shutdown()
        server.server_close()
        thread.join(timeout=2)

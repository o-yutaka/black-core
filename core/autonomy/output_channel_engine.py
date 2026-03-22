from __future__ import annotations

import json
import threading
from datetime import datetime, timezone
from http.server import BaseHTTPRequestHandler, HTTPServer
from pathlib import Path
from typing import Any, Dict, List
from urllib import request

from core.event_bus import EventBus


class OutputChannelEngine:
    """Dispatches autonomous outputs to webhooks, local feed files, and a lightweight API endpoint."""

    def __init__(self, event_bus: EventBus, output_file: str = ".black_memory/autonomy_feed.jsonl") -> None:
        self.event_bus = event_bus
        self.output_file = Path(output_file)
        self.output_file.parent.mkdir(parents=True, exist_ok=True)
        self.latest_payload: Dict[str, Any] = {"status": "idle"}

    def dispatch(self, channels: List[Dict[str, Any]] | None, payload: Dict[str, Any]) -> List[Dict[str, Any]]:
        dispatch_channels = channels or [{"type": "file", "path": str(self.output_file)}]
        reports: List[Dict[str, Any]] = []

        for channel in dispatch_channels:
            channel_type = str(channel.get("type", "file")).lower()
            if channel_type == "webhook":
                report = self._send_webhook(channel, payload)
            elif channel_type == "api":
                report = self._update_api_state(payload)
            else:
                report = self._write_file(channel, payload)
            reports.append(report)
            self.event_bus.publish("output.channel.completed", report)

        summary = {
            "reports": reports,
            "dispatched_at": datetime.now(timezone.utc).isoformat(),
        }
        self.event_bus.publish("output.dispatched", summary)
        return reports

    def start_api_server(self, host: str = "127.0.0.1", port: int = 9091) -> Dict[str, Any]:
        engine = self

        class _Handler(BaseHTTPRequestHandler):
            def do_GET(self):  # noqa: N802
                if self.path not in {"/latest", "/health"}:
                    self.send_response(404)
                    self.end_headers()
                    return
                payload = {"ok": True} if self.path == "/health" else engine.latest_payload
                raw = json.dumps(payload).encode("utf-8")
                self.send_response(200)
                self.send_header("Content-Type", "application/json")
                self.send_header("Content-Length", str(len(raw)))
                self.end_headers()
                self.wfile.write(raw)

            def log_message(self, format, *args):  # noqa: A003
                return

        server = HTTPServer((host, port), _Handler)
        thread = threading.Thread(target=server.serve_forever, daemon=True)
        thread.start()
        startup = {
            "type": "api",
            "success": True,
            "host": host,
            "port": server.server_port,
            "url": f"http://{host}:{server.server_port}/latest",
        }
        self.event_bus.publish("output.api.started", startup)
        return {"server": server, "thread": thread, "info": startup}

    def _write_file(self, channel: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        destination = Path(channel.get("path", self.output_file))
        destination.parent.mkdir(parents=True, exist_ok=True)
        with destination.open("a", encoding="utf-8") as file_handle:
            file_handle.write(json.dumps(payload) + "\n")
        return {"type": "file", "path": str(destination), "success": True}

    def _send_webhook(self, channel: Dict[str, Any], payload: Dict[str, Any]) -> Dict[str, Any]:
        url = str(channel.get("url", ""))
        timeout_seconds = int(channel.get("timeout_seconds", 8))
        body = json.dumps(payload).encode("utf-8")
        req = request.Request(
            url=url,
            method="POST",
            headers={"Content-Type": "application/json", **channel.get("headers", {})},
            data=body,
        )
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
                return {
                    "type": "webhook",
                    "url": url,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300,
                }
        except Exception as error:  # noqa: BLE001
            return {
                "type": "webhook",
                "url": url,
                "status_code": 0,
                "success": False,
                "error": str(error),
            }

    def _update_api_state(self, payload: Dict[str, Any]) -> Dict[str, Any]:
        self.latest_payload = payload
        return {"type": "api", "success": True}

from __future__ import annotations

import json
from datetime import datetime, timezone
from typing import Any, Dict, List
from urllib import parse, request

from core.event_bus import EventBus


class DataIngestionEngine:
    """Collects external signals from web pages, APIs, and social feeds."""

    def __init__(self, event_bus: EventBus, default_timeout_seconds: int = 8) -> None:
        self.event_bus = event_bus
        self.default_timeout_seconds = default_timeout_seconds

    def ingest(self, source_plan: List[Dict[str, Any]] | None) -> Dict[str, Any]:
        sources = source_plan or []
        collected: List[Dict[str, Any]] = []
        for source in sources:
            source_type = str(source.get("type", "api")).lower()
            if source_type == "social":
                entry = self._ingest_social(source)
            elif source_type == "web":
                entry = self._ingest_web(source)
            else:
                entry = self._ingest_api(source)
            collected.append(entry)
            self.event_bus.publish("ingestion.source.completed", entry)

        payload = {
            "signals": collected,
            "signal_count": len(collected),
            "successful_signals": sum(1 for item in collected if item["success"]),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.event_bus.publish("ingestion.completed", payload)
        return payload

    def _ingest_api(self, source: Dict[str, Any]) -> Dict[str, Any]:
        method = str(source.get("method", "GET")).upper()
        url = str(source.get("url", ""))
        if source.get("query"):
            url = f"{url}?{parse.urlencode(source['query'])}"
        body = None
        if source.get("body") is not None:
            body = json.dumps(source["body"]).encode("utf-8")

        req = request.Request(
            url=url,
            method=method,
            data=body,
            headers={"Content-Type": "application/json", **source.get("headers", {})},
        )
        return self._execute_request(source, req)

    def _ingest_web(self, source: Dict[str, Any]) -> Dict[str, Any]:
        req = request.Request(
            url=str(source.get("url", "")),
            method="GET",
            headers={"User-Agent": "BLACK-ORIGIN/1.0", **source.get("headers", {})},
        )
        return self._execute_request(source, req)

    def _ingest_social(self, source: Dict[str, Any]) -> Dict[str, Any]:
        social_query = source.get("query", {})
        normalized_source = {
            **source,
            "method": source.get("method", "GET"),
            "query": social_query,
        }
        return self._ingest_api(normalized_source)

    def _execute_request(self, source: Dict[str, Any], req: request.Request) -> Dict[str, Any]:
        timeout_seconds = int(source.get("timeout_seconds", self.default_timeout_seconds))
        try:
            with request.urlopen(req, timeout=timeout_seconds) as response:  # noqa: S310
                raw_body = response.read().decode("utf-8")
                content_type = response.headers.get("Content-Type", "")
                parsed_body: Any
                if "application/json" in content_type:
                    parsed_body = json.loads(raw_body)
                else:
                    parsed_body = {
                        "excerpt": raw_body[:500],
                        "length": len(raw_body),
                    }
                return {
                    "name": source.get("name", "external-source"),
                    "type": source.get("type", "api"),
                    "url": req.full_url,
                    "status_code": response.status,
                    "success": 200 <= response.status < 300,
                    "body": parsed_body,
                    "captured_at": datetime.now(timezone.utc).isoformat(),
                }
        except Exception as error:  # noqa: BLE001
            return {
                "name": source.get("name", "external-source"),
                "type": source.get("type", "api"),
                "url": req.full_url,
                "status_code": 0,
                "success": False,
                "body": {"error": str(error)},
                "captured_at": datetime.now(timezone.utc).isoformat(),
            }

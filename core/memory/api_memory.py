from __future__ import annotations

import json
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

from core.event_bus import EventBus


class APIMemoryStorage:
    """Persistent API interaction memory used by the knowledge layer."""

    def __init__(self, event_bus: EventBus, storage_dir: str = ".black_memory") -> None:
        self.event_bus = event_bus
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)
        self.memory_path = self.storage / "api_memory.json"
        self.records: List[Dict[str, Any]] = self._load()

    def _load(self) -> List[Dict[str, Any]]:
        if not self.memory_path.exists():
            return []
        return json.loads(self.memory_path.read_text(encoding="utf-8"))

    def _save(self) -> None:
        self.memory_path.write_text(json.dumps(self.records, indent=2, ensure_ascii=False), encoding="utf-8")

    def store(
        self,
        *,
        request: Dict[str, Any],
        response: Dict[str, Any],
        summary: str,
        tags: Optional[List[str]] = None,
    ) -> Dict[str, Any]:
        item = {
            "id": len(self.records),
            "request": request,
            "response": response,
            "summary": summary,
            "tags": tags or [],
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.records.append(item)
        self._save()
        self.event_bus.publish("memory.api_recorded", item)
        return item

    def store_from_action(self, action_result: Dict[str, Any], goal: str, action_name: str) -> Optional[Dict[str, Any]]:
        api_result = action_result.get("api_result")
        if not isinstance(api_result, dict):
            return None

        request = {
            "method": api_result.get("method", "GET"),
            "url": api_result.get("url", ""),
            "status_code": api_result.get("status_code", 0),
        }
        summary = f"Goal={goal}; Action={action_name}; Status={api_result.get('status_code', 0)}"
        return self.store(
            request=request,
            response=api_result,
            summary=summary,
            tags=["action_result", "api"],
        )

    def query(self, *, url_contains: str = "", status_code: Optional[int] = None, top_k: int = 5) -> List[Dict[str, Any]]:
        filtered: List[Dict[str, Any]] = []
        expected_url = url_contains.lower()
        for row in self.records:
            request = row.get("request", {})
            row_url = str(request.get("url", "")).lower()
            row_status = int(request.get("status_code", row.get("response", {}).get("status_code", 0)))

            if expected_url and expected_url not in row_url:
                continue
            if status_code is not None and row_status != status_code:
                continue
            filtered.append(row)

        filtered.sort(key=lambda x: x.get("created_at", ""), reverse=True)
        payload = {
            "url_contains": url_contains,
            "status_code": status_code,
            "returned": len(filtered[:top_k]),
        }
        self.event_bus.publish("memory.api_queried", payload)
        return filtered[:top_k]

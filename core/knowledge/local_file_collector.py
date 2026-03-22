from __future__ import annotations

import hashlib
from pathlib import Path
from typing import Any, Dict, Iterable, List

from core.event_bus import EventBus


class LocalFileCollector:
    """Collects text knowledge from local files for routing into intelligence loop."""

    def __init__(self, event_bus: EventBus, max_file_size: int = 128_000) -> None:
        self.event_bus = event_bus
        self.max_file_size = max_file_size

    def collect(self, paths: Iterable[str]) -> List[Dict[str, Any]]:
        candidate_paths = list(paths)
        documents: List[Dict[str, Any]] = []
        for raw_path in candidate_paths:
            path = Path(raw_path)
            if not path.exists() or not path.is_file():
                continue
            if path.stat().st_size > self.max_file_size:
                continue

            text = path.read_text(encoding="utf-8", errors="ignore").strip()
            if not text:
                continue

            digest = hashlib.sha256(text.encode("utf-8")).hexdigest()[:12]
            documents.append(
                {
                    "path": str(path),
                    "filename": path.name,
                    "size": path.stat().st_size,
                    "hash": digest,
                    "content": text,
                }
            )

        self.event_bus.publish("knowledge.local_collected", {"documents": len(documents), "paths": candidate_paths})
        return documents

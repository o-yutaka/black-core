from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict

from core.event_bus import EventBus


@dataclass
class RuntimeEngine:
    event_bus: EventBus
    running: bool = False
    cycle: int = 0
    metadata: Dict[str, Any] = field(default_factory=dict)

    def start(self) -> None:
        self.running = True
        self.event_bus.publish("runtime.started", {"cycle": self.cycle, "at": self._utc_now()})

    def stop(self, reason: str = "manual") -> None:
        self.running = False
        self.event_bus.publish(
            "runtime.stopped",
            {"cycle": self.cycle, "reason": reason, "at": self._utc_now()},
        )

    def tick(self, state: Dict[str, Any]) -> Dict[str, Any]:
        if not self.running:
            raise RuntimeError("RuntimeEngine is not running")

        self.cycle += 1
        snapshot = {
            "cycle": self.cycle,
            "state": state,
            "at": self._utc_now(),
        }
        self.event_bus.publish("runtime.tick", snapshot)
        return snapshot

    @staticmethod
    def _utc_now() -> str:
        return datetime.now(timezone.utc).isoformat()

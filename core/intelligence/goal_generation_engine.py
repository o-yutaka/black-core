from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict

from core.event_bus import EventBus


class GoalGenerationEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def generate(self, runtime_snapshot: Dict[str, Any]) -> Dict[str, Any]:
        goal = runtime_snapshot["state"].get("goal", "Improve autonomous execution reliability")
        payload = {
            "goal": goal,
            "cycle": runtime_snapshot["cycle"],
            "context": runtime_snapshot["state"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.event_bus.publish("goal.generated", payload)
        return payload

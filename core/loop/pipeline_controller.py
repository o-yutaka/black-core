from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Callable, Dict, Iterable, List

from core.event_bus import EventBus


StageHandler = Callable[[Dict[str, Any]], Dict[str, Any]]


@dataclass
class PipelineStage:
    name: str
    handler: StageHandler


class PipelineController:
    """Enforces deterministic step-by-step execution of the core loop."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def run(self, initial_payload: Dict[str, Any], stages: Iterable[PipelineStage]) -> Dict[str, Any]:
        payload = dict(initial_payload)
        executed: List[str] = []

        for order, stage in enumerate(stages, start=1):
            self.event_bus.publish(
                "pipeline.stage.started",
                {"stage": stage.name, "order": order, "keys": sorted(payload.keys())},
            )
            stage_result = stage.handler(payload)
            if not isinstance(stage_result, dict):
                raise TypeError(f"Pipeline stage '{stage.name}' must return dict, got {type(stage_result)}")

            payload.update(stage_result)
            executed.append(stage.name)
            self.event_bus.publish(
                "pipeline.stage.completed",
                {"stage": stage.name, "order": order, "result_keys": sorted(stage_result.keys())},
            )

        self.event_bus.publish(
            "pipeline.completed",
            {"stages": executed, "total_stages": len(executed), "keys": sorted(payload.keys())},
        )
        return payload

from __future__ import annotations

from collections import defaultdict
from typing import Any, Callable, DefaultDict, Dict, List


class EventBus:
    """In-process pub/sub event bus for BLACK ORIGIN core engines."""

    def __init__(self) -> None:
        self._handlers: DefaultDict[str, List[Callable[[Dict[str, Any]], None]]] = defaultdict(list)

    def publish(self, topic: str, payload: Dict[str, Any]) -> None:
        for handler in self._handlers.get(topic, []):
            handler(payload)
        for handler in self._handlers.get("*", []):
            handler({"topic": topic, "payload": payload})

    def subscribe(self, topic: str, handler: Callable[[Dict[str, Any]], None]) -> Callable[[], None]:
        self._handlers[topic].append(handler)

        def unsubscribe() -> None:
            if handler in self._handlers[topic]:
                self._handlers[topic].remove(handler)

        return unsubscribe

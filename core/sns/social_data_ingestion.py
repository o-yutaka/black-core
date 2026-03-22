from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List

from core.event_bus import EventBus


@dataclass
class SocialSignal:
    source: str
    topic: str
    engagement: float
    velocity: float
    sentiment: float

    @property
    def virality_score(self) -> float:
        return (0.5 * self.engagement) + (0.35 * self.velocity) + (0.15 * max(0.0, self.sentiment))


class SocialDataIngestion:
    """Ingests social trend signals from X/Reddit payloads provided in runtime context."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def ingest(self, context: Dict[str, Any]) -> List[Dict[str, Any]]:
        sns_context = context.get("sns", {})
        x_rows = sns_context.get("x_trends", [])
        reddit_rows = sns_context.get("reddit_trends", [])

        normalized: List[SocialSignal] = []
        normalized.extend(self._normalize_rows("x", x_rows))
        normalized.extend(self._normalize_rows("reddit", reddit_rows))

        signals = [
            {
                "source": row.source,
                "topic": row.topic,
                "engagement": row.engagement,
                "velocity": row.velocity,
                "sentiment": row.sentiment,
                "virality_score": row.virality_score,
            }
            for row in sorted(normalized, key=lambda item: item.virality_score, reverse=True)
        ]

        self.event_bus.publish("sns.ingestion.completed", {"count": len(signals), "signals": signals})
        return signals

    def _normalize_rows(self, source: str, rows: List[Dict[str, Any]]) -> List[SocialSignal]:
        normalized: List[SocialSignal] = []
        for row in rows:
            topic = str(row.get("topic", "")).strip()
            if not topic:
                continue
            normalized.append(
                SocialSignal(
                    source=source,
                    topic=topic,
                    engagement=float(row.get("engagement", 0.0)),
                    velocity=float(row.get("velocity", 0.0)),
                    sentiment=float(row.get("sentiment", 0.0)),
                )
            )
        return normalized

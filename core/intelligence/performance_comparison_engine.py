from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict

from core.event_bus import EventBus


@dataclass
class PerformanceGap:
    simulated_engagement: float
    real_engagement: float
    delta: float
    ratio: float


class PerformanceComparisonEngine:
    """Compares simulated campaign outcomes with real SNS metrics and suggests strategy updates."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def compare(self, simulation: Dict[str, Any], real_metrics: Dict[str, Any], strategy: str) -> Dict[str, Any]:
        simulated_score = self._simulation_score(simulation)
        real_score = self._real_score(real_metrics)
        delta = real_score - simulated_score
        ratio = (real_score / simulated_score) if simulated_score > 0 else 0.0

        gap = PerformanceGap(
            simulated_engagement=simulated_score,
            real_engagement=real_score,
            delta=delta,
            ratio=ratio,
        )

        adjustment = self._adjustment(gap=gap, strategy=strategy)
        payload = {
            "strategy": strategy,
            "gap": {
                "simulated_engagement": gap.simulated_engagement,
                "real_engagement": gap.real_engagement,
                "delta": gap.delta,
                "ratio": gap.ratio,
            },
            "adjustment": adjustment,
        }
        self.event_bus.publish("performance.compared", payload)
        return payload

    @staticmethod
    def _simulation_score(simulation: Dict[str, Any]) -> float:
        metrics = simulation.get("metrics", simulation)
        likes = float(metrics.get("likes", 0.0))
        reposts = float(metrics.get("reposts", 0.0))
        replies = float(metrics.get("replies", 0.0))
        quotes = float(metrics.get("quotes", 0.0))
        impressions = float(metrics.get("impressions", 0.0))
        return likes + (2.0 * reposts) + (1.5 * replies) + (2.5 * quotes) + (0.01 * impressions)

    @staticmethod
    def _real_score(real_metrics: Dict[str, Any]) -> float:
        source = real_metrics.get("public_metrics", real_metrics)
        likes = float(source.get("like_count", source.get("likes", 0.0)))
        reposts = float(source.get("retweet_count", source.get("reposts", 0.0)))
        replies = float(source.get("reply_count", source.get("replies", 0.0)))
        quotes = float(source.get("quote_count", source.get("quotes", 0.0)))
        impressions = float(source.get("impression_count", source.get("impressions", 0.0)))
        return likes + (2.0 * reposts) + (1.5 * replies) + (2.5 * quotes) + (0.01 * impressions)

    @staticmethod
    def _adjustment(gap: PerformanceGap, strategy: str) -> Dict[str, Any]:
        if gap.simulated_engagement <= 0 and gap.real_engagement <= 0:
            return {
                "next_strategy": f"{strategy}:increase-distribution",
                "confidence": 0.45,
                "notes": "No measurable engagement; broaden targeting and test posting windows.",
            }

        if gap.delta >= 5.0:
            return {
                "next_strategy": f"{strategy}:scale",
                "confidence": 0.85,
                "notes": "Real performance beats simulation. Scale current style and cadence.",
            }

        if gap.delta <= -5.0:
            return {
                "next_strategy": f"{strategy}:recalibrate",
                "confidence": 0.35,
                "notes": "Real performance trails simulation. Tighten copy, timing, and audience hypotheses.",
            }

        return {
            "next_strategy": f"{strategy}:refine",
            "confidence": 0.6,
            "notes": "Performance near simulation. Run focused A/B iterations.",
        }

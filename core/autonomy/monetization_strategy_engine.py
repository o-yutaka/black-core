from __future__ import annotations

from datetime import datetime, timezone
from typing import Any, Dict, List

from core.event_bus import EventBus


class MonetizationStrategyEngine:
    """Builds actionable revenue strategies using current goal analysis and external signals."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def build_strategy(self, analysis: Dict[str, Any], ingestion_report: Dict[str, Any]) -> Dict[str, Any]:
        signals = ingestion_report.get("signals", [])
        offers = self._derive_offers(signals, analysis)
        primary_offer = offers[0] if offers else self._fallback_offer(analysis)
        strategy = {
            "goal": analysis["goal"],
            "strategy": analysis.get("recommended_strategy", "balanced-execution"),
            "primary_offer": primary_offer,
            "offers": offers,
            "projected_revenue": round(sum(item["projected_revenue"] for item in offers), 2),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
        self.event_bus.publish("monetization.strategy.generated", strategy)
        return strategy

    def _derive_offers(self, signals: List[Dict[str, Any]], analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        offers: List[Dict[str, Any]] = []
        success_bonus = 1.2 if analysis.get("top_strategies") else 0.8

        for signal in signals:
            if not signal.get("success"):
                continue
            source_type = str(signal.get("type", "api"))
            source_name = str(signal.get("name", "external-source"))
            confidence = 0.65 if source_type == "social" else 0.75

            if source_type == "social":
                channel = "sponsored_content"
                conversion_rate = 0.025
                avg_order_value = 45.0
            elif source_type == "web":
                channel = "affiliate_offer"
                conversion_rate = 0.02
                avg_order_value = 62.0
            else:
                channel = "api_lead_gen"
                conversion_rate = 0.035
                avg_order_value = 80.0

            audience_estimate = 1000 + (150 * len(str(signal.get("body", {}))))
            projected_revenue = audience_estimate * conversion_rate * avg_order_value * success_bonus
            offers.append(
                {
                    "offer_name": f"{source_name}-{channel}",
                    "channel": channel,
                    "confidence": round(confidence * success_bonus, 3),
                    "audience_estimate": int(audience_estimate),
                    "projected_revenue": round(projected_revenue, 2),
                }
            )

        offers.sort(key=lambda item: item["projected_revenue"], reverse=True)
        return offers[:5]

    def _fallback_offer(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "offer_name": f"{analysis['goal'][:24]}-subscription",
            "channel": "subscription_upsell",
            "confidence": 0.45,
            "audience_estimate": 500,
            "projected_revenue": 500 * 0.015 * 25.0,
        }

from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class MonetizationSignal:
    name: str
    value: float
    rationale: str


class MonetizationScorer:
    """Scores goals/context for expected revenue impact and conversion potential."""

    _KEYWORD_WEIGHTS = {
        "revenue": 0.28,
        "profit": 0.24,
        "conversion": 0.22,
        "upsell": 0.18,
        "retention": 0.14,
        "pricing": 0.16,
        "margin": 0.16,
    }

    def score(self, goal: str, context: Dict[str, Any], best_practices: List[Dict[str, Any]]) -> Dict[str, Any]:
        normalized_goal = goal.lower()

        signals: List[MonetizationSignal] = []
        keyword_score = 0.0
        for keyword, weight in self._KEYWORD_WEIGHTS.items():
            if keyword in normalized_goal:
                keyword_score += weight
                signals.append(
                    MonetizationSignal(
                        name=f"goal_keyword:{keyword}",
                        value=weight,
                        rationale=f"Goal references '{keyword}'",
                    )
                )

        context_signal = self._score_context(context)
        if context_signal.value > 0:
            signals.append(context_signal)

        memory_lift = min(0.35, 0.08 * len(best_practices))
        if memory_lift > 0:
            signals.append(
                MonetizationSignal(
                    name="memory_best_practices",
                    value=memory_lift,
                    rationale="Memory contains reusable high-importance practices",
                )
            )

        raw_score = keyword_score + context_signal.value + memory_lift
        profit_score = round(min(1.0, max(0.05, raw_score)), 4)

        conversion_bias = round(min(1.0, 0.35 + (profit_score * 0.55)), 4)
        return {
            "profit_score": profit_score,
            "conversion_bias": conversion_bias,
            "signals": [signal.__dict__ for signal in signals],
            "is_high_value": profit_score >= 0.6,
        }

    def _score_context(self, context: Dict[str, Any]) -> MonetizationSignal:
        score = 0.0
        rationale_parts: List[str] = []

        for key, value in context.items():
            key_l = str(key).lower()
            if any(token in key_l for token in ("revenue", "profit", "price", "conversion", "customer")):
                score += 0.12
                rationale_parts.append(f"context key '{key}' indicates monetization")
            if isinstance(value, (int, float)) and value > 0:
                score += min(0.12, float(value) / 100.0)
            elif isinstance(value, bool) and value:
                score += 0.04
            elif isinstance(value, str) and any(token in value.lower() for token in ("paid", "purchase", "upgrade")):
                score += 0.08

        score = min(0.5, score)
        return MonetizationSignal(
            name="context_monetization_strength",
            value=round(score, 4),
            rationale=", ".join(rationale_parts) if rationale_parts else "No monetization-specific context keys found",
        )

from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List


class CodeGenerationEngine:
    """Builds executable Python code from a multi-agent selected plan."""

    def generate(
        self,
        goal: str,
        context: Dict[str, Any],
        selected_plan: Dict[str, Any],
        discussion: List[Dict[str, Any]],
        conversion_profile: Dict[str, Any] | None = None,
    ) -> str:
        safe_goal = goal.replace('"', "'")
        safe_strategy = selected_plan.get("strategy", "balanced-execution").replace('"', "'")
        algo = selected_plan.get("algorithm", "weighted-priority-selection").replace('"', "'")

        context_weights = self._extract_context_weights(context)
        critique_count = sum(len(item.get("issues", [])) for item in discussion)
        conversion_profile = conversion_profile or {}
        conversion_bias = float(conversion_profile.get("conversion_bias", 0.45))
        cta_strength = str(conversion_profile.get("cta_strength", "moderate"))

        return (
            dedent(
                f"""
                from __future__ import annotations
                import json

                GOAL = \"{safe_goal}\"
                STRATEGY = \"{safe_strategy}\"
                ALGORITHM = \"{algo}\"
                CONTEXT_WEIGHTS = {context_weights}
                CRITIQUE_COUNT = {critique_count}
                CONVERSION_BIAS = {conversion_bias}
                CTA_STRENGTH = "{cta_strength}"

                def build_candidates(weights):
                    candidates = []
                    for key, value in weights.items():
                        priority = float(value) if isinstance(value, (int, float)) else float(len(str(value)))
                        candidate_score = (priority * 0.7) + (1.0 / (1.0 + abs(priority - 5.0)))
                        candidates.append((key, round(candidate_score, 4)))
                    if not candidates:
                        candidates = [("default_action", 1.0)]
                    return sorted(candidates, key=lambda item: item[1], reverse=True)

                def select_action(candidates):
                    winner = candidates[0]
                    confidence = round(min(0.99, 0.45 + winner[1] / 10.0 - (CRITIQUE_COUNT * 0.01)), 4)
                    return winner, max(0.05, confidence)

                candidates = build_candidates(CONTEXT_WEIGHTS)
                winner, confidence = select_action(candidates)
                conversion_score = round(min(0.99, (confidence * 0.6) + (CONVERSION_BIAS * 0.4)), 4)
                result = {{
                    "goal": GOAL,
                    "strategy": STRATEGY,
                    "algorithm": ALGORITHM,
                    "selected_action": winner[0],
                    "score": winner[1],
                    "confidence": confidence,
                    "candidate_count": len(candidates),
                    "conversion_score": conversion_score,
                    "cta": "Buy now" if CTA_STRENGTH == "high" else "Learn more",
                }}
                print(json.dumps(result, sort_keys=True))
                """
            ).strip()
            + "\n"
        )

    @staticmethod
    def _extract_context_weights(context: Dict[str, Any]) -> Dict[str, float]:
        weights: Dict[str, float] = {}
        for key, value in context.items():
            if isinstance(value, bool):
                weights[key] = 2.0 if value else 0.5
            elif isinstance(value, (int, float)):
                weights[key] = float(value)
            elif isinstance(value, str):
                weights[key] = float(len(value))
            elif isinstance(value, dict):
                weights[key] = float(len(value.keys()))
            elif isinstance(value, list):
                weights[key] = float(len(value))
        return weights

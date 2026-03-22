from __future__ import annotations

from textwrap import dedent
from typing import Any, Dict, List


class CodeGenerationEngine:
    """Builds executable Python code from a multi-agent selected plan."""

    def generate(self, goal: str, context: Dict[str, Any], selected_plan: Dict[str, Any], discussion: List[Dict[str, Any]], iteration: int = 1, prior_error: str = "") -> str:
        safe_goal = goal.replace('"', "'")
        safe_strategy = selected_plan.get("strategy", "balanced-execution").replace('"', "'")
        algo = selected_plan.get("algorithm", "weighted-priority-selection").replace('"', "'")

        context_weights = self._extract_context_weights(context)
        critique_count = sum(len(item.get("issues", [])) for item in discussion)
        safe_error = prior_error.replace("\n", " ").replace("\"", "'")[:160]

        return dedent(
            f"""
            from __future__ import annotations
            import json

            GOAL = \"{safe_goal}\"
            STRATEGY = \"{safe_strategy}\"
            ALGORITHM = \"{algo}\"
            CONTEXT_WEIGHTS = {context_weights}
            CRITIQUE_COUNT = {critique_count}
            ITERATION = {iteration}
            PRIOR_ERROR = "{safe_error}"

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
                improvement_bias = min(0.15, ITERATION * 0.03)
                error_penalty = 0.08 if PRIOR_ERROR else 0.0
                confidence = round(min(0.99, 0.45 + winner[1] / 10.0 + improvement_bias - (CRITIQUE_COUNT * 0.01) - error_penalty), 4)
                return winner, max(0.05, confidence)

            candidates = build_candidates(CONTEXT_WEIGHTS)
            winner, confidence = select_action(candidates)
            result = {{
                "goal": GOAL,
                "strategy": STRATEGY,
                "algorithm": ALGORITHM,
                "selected_action": winner[0],
                "score": winner[1],
                "confidence": confidence,
                "candidate_count": len(candidates),
                "iteration": ITERATION,
                "prior_error": PRIOR_ERROR,
            }}
            print(json.dumps(result, sort_keys=True))
            """
        ).strip() + "\n"

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

    def refine(
        self,
        goal: str,
        context: Dict[str, Any],
        selected_plan: Dict[str, Any],
        discussion: List[Dict[str, Any]],
        previous_result: Dict[str, Any],
        attempt: int,
    ) -> str:
        return self.generate(
            goal=goal,
            context=context,
            selected_plan=selected_plan,
            discussion=discussion,
            iteration=attempt,
            prior_error=str(previous_result.get("stderr", "")) or str(previous_result.get("summary", "")),
        )

from __future__ import annotations

from typing import Any, Dict, List

from core.event_bus import EventBus


class InterviewEngine:
    """Inversion-style interview pass that clarifies goal intent before planning."""

    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus

    def conduct(self, analysis: Dict[str, Any]) -> Dict[str, Any]:
        goal = analysis["goal"]
        context = analysis.get("context", {})

        questions = self._build_questions(goal=goal, context=context, analysis=analysis)
        answers = self._derive_answers(goal=goal, context=context, analysis=analysis, questions=questions)
        constraints = self._derive_constraints(context=context)
        risk_register = self._derive_risks(analysis=analysis)

        interview = {
            "questions": questions,
            "answers": answers,
            "constraints": constraints,
            "risk_register": risk_register,
            "clarified_goal": self._clarify_goal(goal=goal, constraints=constraints),
            "confidence": self._confidence_score(risk_register=risk_register, answers=answers),
        }

        enriched_analysis = {
            **analysis,
            "goal": interview["clarified_goal"],
            "interview": interview,
        }
        self.event_bus.publish("interview.completed", enriched_analysis)
        return enriched_analysis

    def _build_questions(self, goal: str, context: Dict[str, Any], analysis: Dict[str, Any]) -> List[str]:
        questions = [
            f"What is the highest-impact measurable outcome for '{goal}' this cycle?",
            "Which system constraint must never be violated during execution?",
        ]
        if context.get("environment"):
            questions.append(f"How should execution differ in {context['environment']} environment?")
        if analysis.get("failed_strategies"):
            questions.append("Which historically failed strategy must be explicitly avoided?")
        return questions

    def _derive_answers(
        self,
        goal: str,
        context: Dict[str, Any],
        analysis: Dict[str, Any],
        questions: List[str],
    ) -> List[Dict[str, str]]:
        avoided = analysis.get("failed_strategies", [])
        environment = context.get("environment", "unknown")

        answer_bank = [
            f"Primary outcome: maximize verified progress toward '{goal}'.",
            "Hard constraint: preserve runtime stability and avoid destructive actions.",
            f"Environment profile: {environment} with conservative risk posture.",
            f"Avoided strategies: {', '.join(avoided) if avoided else 'none recorded'}.",
        ]

        return [{"question": q, "answer": answer_bank[min(i, len(answer_bank) - 1)]} for i, q in enumerate(questions)]

    def _derive_constraints(self, context: Dict[str, Any]) -> List[str]:
        constraints = ["must_preserve_runtime", "must_emit_observable_events"]
        if "latency_budget" in context:
            constraints.append(f"latency_budget={context['latency_budget']}")
        if context.get("target"):
            constraints.append(f"target={context['target']}")
        return constraints

    def _derive_risks(self, analysis: Dict[str, Any]) -> List[Dict[str, Any]]:
        risks: List[Dict[str, Any]] = []
        for strategy in analysis.get("failed_strategies", []):
            risks.append({"risk": "strategy_regression", "strategy": strategy, "severity": "high"})
        if not analysis.get("memory_hits"):
            risks.append({"risk": "novel_goal", "strategy": "n/a", "severity": "medium"})
        return risks

    def _clarify_goal(self, goal: str, constraints: List[str]) -> str:
        return f"{goal} | constraints: {';'.join(constraints)}"

    def _confidence_score(self, risk_register: List[Dict[str, Any]], answers: List[Dict[str, str]]) -> float:
        base = 0.85 if answers else 0.6
        penalty = min(0.35, 0.1 * len(risk_register))
        return round(max(0.1, base - penalty), 3)

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict, List

from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.memory.faiss_memory import FaissMemory


class TaskIntelligenceEngine:
    def __init__(self, event_bus: EventBus, memory: "FaissMemory") -> None:
        self.event_bus = event_bus
        self.memory = memory

    def analyze(self, goal_pack: Dict[str, Any]) -> Dict[str, Any]:
        goal = goal_pack["goal"]
        context = goal_pack.get("context", {})

        memory_hits = self.memory.search_memory(goal, top_k=7)
        top_strategies = self.memory.top_strategies(top_k=5)
        failed_strategies = self.memory.failed_strategies(top_k=5)
        best_practices = self.memory.best_practices(top_k=3)

        recommended_strategy = (
            top_strategies[0]["strategy"]
            if top_strategies
            else (memory_hits[0]["strategy"] if memory_hits else "balanced-execution")
        )

        generated_tasks = self._generate_high_value_tasks(
            goal=goal,
            context=context,
            top_strategies=top_strategies,
            failed_strategies=failed_strategies,
            best_practices=best_practices,
            memory_hits=memory_hits,
        )
        self.event_bus.publish("tasks.generated", {"goal": goal, "tasks": generated_tasks})

        analysis = {
            "goal": goal,
            "context": context,
            "memory_hits": memory_hits,
            "top_strategies": top_strategies,
            "failed_strategies": failed_strategies,
            "best_practices": best_practices,
            "recommended_strategy": recommended_strategy,
            "generated_tasks": generated_tasks,
        }
        self.event_bus.publish("analysis.completed", analysis)
        return analysis

    def evaluate_and_remember(
        self,
        goal: str,
        strategy: str,
        action_name: str,
        result: Dict[str, Any],
    ) -> Dict[str, Any]:
        success = bool(result.get("success", False))
        reward = float(result.get("reward", 0.0))
        importance = min(1.0, 0.4 + max(0.0, reward) * 0.3 + (0.3 if success else 0.0))

        stored = self.memory.save_memory(
            text=f"Goal={goal}; Action={action_name}; Summary={result.get('summary', '')}",
            strategy=strategy,
            importance=importance,
            success=success,
            reward=reward,
            context={"goal": goal, "action": {"name": action_name, "result": result}},
        )

        evaluation = {"success": success, "reward": reward, "stored_memory": stored}
        self.event_bus.publish("evaluation.completed", evaluation)
        self.event_bus.publish("memory.recorded", stored)
        return evaluation

    def _generate_high_value_tasks(
        self,
        goal: str,
        context: Dict[str, Any],
        top_strategies: List[Dict[str, Any]],
        failed_strategies: List[str],
        best_practices: List[Dict[str, Any]],
        memory_hits: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        strategy = top_strategies[0]["strategy"] if top_strategies else "balanced-execution"

        candidate_tasks = [
            {
                "name": "automate-high-impact-workflow",
                "objective": f"Automate the highest-impact workflow supporting goal: {goal}",
                "impact": self._estimate_impact(context, boost=0.2),
                "automation_potential": self._estimate_automation(context, boost=0.25),
                "feasibility": self._estimate_feasibility(context, failed_strategies, penalty=0.05),
                "strategy": strategy,
                "reason": "Direct automation produces persistent ROI and reduces repeat manual work.",
                "kind": "execution",
            },
            {
                "name": "build-reliability-guardrails",
                "objective": "Implement measurable guardrails that prevent regression and silent failures.",
                "impact": self._estimate_impact(context, boost=0.15),
                "automation_potential": self._estimate_automation(context, boost=0.2),
                "feasibility": self._estimate_feasibility(context, failed_strategies, penalty=0.0),
                "strategy": strategy,
                "reason": "Reliability guardrails create compounding value across every future task run.",
                "kind": "execution",
            },
            {
                "name": "summarize-context-without-action",
                "objective": "Generate passive summary output only.",
                "impact": 0.15,
                "automation_potential": 0.1,
                "feasibility": 0.95,
                "strategy": "documentation-only",
                "reason": "Low-value passive output candidate used for filtering quality control.",
                "kind": "meta",
            },
            {
                "name": "close-memory-gap",
                "objective": "Fill memory gaps by adding evaluation probes for unknown high-risk areas.",
                "impact": self._estimate_impact(context, boost=0.1),
                "automation_potential": self._estimate_automation(context, boost=0.15),
                "feasibility": self._estimate_feasibility(context, failed_strategies, penalty=0.1),
                "strategy": strategy,
                "reason": "Targeted probes improve downstream decision quality and reduce uncertainty.",
                "kind": "learning",
            },
        ]

        for candidate in candidate_tasks:
            candidate["value_score"] = round(
                (candidate["impact"] * 0.45)
                + (candidate["automation_potential"] * 0.35)
                + (candidate["feasibility"] * 0.2),
                4,
            )
            candidate["confidence"] = self._confidence_from_memory(
                task_name=candidate["name"],
                strategy=candidate["strategy"],
                memory_hits=memory_hits,
                best_practices=best_practices,
            )

        filtered = [
            task
            for task in candidate_tasks
            if task["value_score"] >= 0.5
            and task["automation_potential"] >= 0.45
            and task["kind"] != "meta"
            and task["strategy"] not in failed_strategies
        ]

        filtered.sort(
            key=lambda task: (task["value_score"], task["confidence"], task["impact"]),
            reverse=True,
        )
        return filtered[:3]

    @staticmethod
    def _estimate_impact(context: Dict[str, Any], boost: float = 0.0) -> float:
        size_factor = min(1.0, 0.3 + (0.06 * len(context)))
        urgency = 0.2 if context.get("production") or context.get("urgent") else 0.0
        return round(min(1.0, size_factor + urgency + boost), 4)

    @staticmethod
    def _estimate_automation(context: Dict[str, Any], boost: float = 0.0) -> float:
        numeric_signals = sum(1 for value in context.values() if isinstance(value, (int, float, bool)))
        structured_signals = sum(1 for value in context.values() if isinstance(value, (dict, list)))
        baseline = 0.35 + min(0.35, numeric_signals * 0.08) + min(0.2, structured_signals * 0.05)
        return round(min(1.0, baseline + boost), 4)

    @staticmethod
    def _estimate_feasibility(context: Dict[str, Any], failed_strategies: List[str], penalty: float = 0.0) -> float:
        complexity_penalty = min(0.25, 0.03 * len(context))
        historical_penalty = min(0.2, 0.04 * len(failed_strategies))
        score = 0.85 - complexity_penalty - historical_penalty - penalty
        return round(max(0.2, score), 4)

    @staticmethod
    def _confidence_from_memory(
        task_name: str,
        strategy: str,
        memory_hits: List[Dict[str, Any]],
        best_practices: List[Dict[str, Any]],
    ) -> float:
        matches = sum(1 for item in memory_hits if item.get("strategy") == strategy and item.get("success", False))
        best_practice_match = any(item.get("strategy") == strategy for item in best_practices)
        confidence = 0.45 + min(0.35, matches * 0.08) + (0.1 if best_practice_match else 0.0)
        if "guardrails" in task_name:
            confidence += 0.03
        return round(min(0.99, confidence), 4)

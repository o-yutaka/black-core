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
        strategy_health = self._build_strategy_health(memory_hits, top_strategies, failed_strategies)

        recommended_strategy = (
            strategy_health[0]["strategy"]
            if strategy_health
            else (memory_hits[0]["strategy"] if memory_hits else "balanced-execution")
        )

        generated_tasks = self._generate_high_value_tasks(
            goal=goal,
            context=context,
            strategy_health=strategy_health,
            best_practices=best_practices,
            memory_hits=memory_hits,
        )
        self.event_bus.publish("tasks.generated", {"goal": goal, "tasks": generated_tasks, "strategy_health": strategy_health})

        analysis = {
            "goal": goal,
            "context": context,
            "memory_hits": memory_hits,
            "top_strategies": top_strategies,
            "failed_strategies": failed_strategies,
            "best_practices": best_practices,
            "strategy_health": strategy_health,
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
        strategy_health: List[Dict[str, Any]],
        best_practices: List[Dict[str, Any]],
        memory_hits: List[Dict[str, Any]],
    ) -> List[Dict[str, Any]]:
        strategy = strategy_health[0]["strategy"] if strategy_health else "balanced-execution"
        strategy_success_rate = strategy_health[0]["success_rate"] if strategy_health else 0.65
        strategy_threshold = 0.55

        candidate_tasks = [
            {
                "name": "automate-high-impact-workflow",
                "objective": f"Automate the highest-impact workflow supporting goal: {goal}",
                "impact": self._estimate_impact(context, boost=0.2),
                "automation_potential": self._estimate_automation(context, boost=0.25),
                "feasibility": self._estimate_feasibility(context, strategy_success_rate, penalty=0.05),
                "strategy": strategy,
                "strategy_success_rate": strategy_success_rate,
                "reason": "Direct automation produces persistent ROI and reduces repeat manual work.",
                "kind": "execution",
            },
            {
                "name": "build-reliability-guardrails",
                "objective": "Implement measurable guardrails that prevent regression and silent failures.",
                "impact": self._estimate_impact(context, boost=0.15),
                "automation_potential": self._estimate_automation(context, boost=0.2),
                "feasibility": self._estimate_feasibility(context, strategy_success_rate, penalty=0.0),
                "strategy": strategy,
                "strategy_success_rate": strategy_success_rate,
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
                "strategy_success_rate": 0.3,
                "reason": "Low-value passive output candidate used for filtering quality control.",
                "kind": "meta",
            },
            {
                "name": "close-memory-gap",
                "objective": "Fill memory gaps by adding evaluation probes for unknown high-risk areas.",
                "impact": self._estimate_impact(context, boost=0.1),
                "automation_potential": self._estimate_automation(context, boost=0.15),
                "feasibility": self._estimate_feasibility(context, strategy_success_rate, penalty=0.1),
                "strategy": strategy,
                "strategy_success_rate": strategy_success_rate,
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
            candidate["final_score"] = round(
                (candidate["value_score"] * 0.75) + (candidate["strategy_success_rate"] * 0.25),
                4,
            )

        filtered = [
            task
            for task in candidate_tasks
            if task["value_score"] >= 0.5
            and task["automation_potential"] >= 0.45
            and task["kind"] != "meta"
            and task["strategy_success_rate"] >= strategy_threshold
        ]

        filtered.sort(
            key=lambda task: (task["final_score"], task["confidence"], task["impact"]),
            reverse=True,
        )
        return filtered[:3]

    @staticmethod
    def _build_strategy_health(
        memory_hits: List[Dict[str, Any]],
        top_strategies: List[Dict[str, Any]],
        failed_strategies: List[str],
    ) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, float]] = {}
        for hit in memory_hits:
            strategy = str(hit.get("strategy", "balanced-execution"))
            record = grouped.setdefault(strategy, {"wins": 0.0, "total": 0.0, "prior": 0.0})
            record["total"] += 1.0
            if bool(hit.get("success", False)):
                record["wins"] += 1.0

        for item in top_strategies:
            strategy = str(item.get("strategy", "balanced-execution"))
            record = grouped.setdefault(strategy, {"wins": 0.0, "total": 0.0, "prior": 0.0})
            record["prior"] = float(item.get("win_rate", 0.0))

        insights: List[Dict[str, Any]] = []
        for strategy, metrics in grouped.items():
            total = metrics["total"]
            observed_rate = (metrics["wins"] / total) if total > 0 else 0.0
            has_observations = total > 0
            prior_rate = metrics["prior"]
            # Blend observed outcomes with prior topline win rate.
            success_rate = (observed_rate * 0.75 + prior_rate * 0.25) if has_observations else max(prior_rate, 0.5)
            failure_flag_penalty = 0.05 if strategy in failed_strategies else 0.0
            adjusted_rate = max(0.0, min(1.0, success_rate - failure_flag_penalty))
            insights.append(
                {
                    "strategy": strategy,
                    "success_rate": round(adjusted_rate, 4),
                    "observations": int(total),
                    "failed_flag": strategy in failed_strategies,
                }
            )

        if not insights:
            insights = [{"strategy": "balanced-execution", "success_rate": 0.65, "observations": 0, "failed_flag": False}]

        insights.sort(key=lambda item: (item["success_rate"], item["observations"]), reverse=True)
        return insights

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
    def _estimate_feasibility(context: Dict[str, Any], strategy_success_rate: float, penalty: float = 0.0) -> float:
        complexity_penalty = min(0.25, 0.03 * len(context))
        strategy_bonus = min(0.15, max(0.0, strategy_success_rate - 0.5) * 0.3)
        score = 0.7 - complexity_penalty + strategy_bonus - penalty
        return round(max(0.2, min(0.98, score)), 4)

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

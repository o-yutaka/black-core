from __future__ import annotations

from typing import TYPE_CHECKING, Any, Dict

from core.event_bus import EventBus

if TYPE_CHECKING:
    from core.memory.faiss_memory import FaissMemory


class TaskIntelligenceEngine:
    def __init__(self, event_bus: EventBus, memory: "FaissMemory") -> None:
        self.event_bus = event_bus
        self.memory = memory

    def analyze(self, goal_pack: Dict[str, Any]) -> Dict[str, Any]:
        goal = goal_pack["goal"]
        memory_hits = self.memory.search_memory(goal, top_k=7)
        top_strategies = self.memory.top_strategies(top_k=5)

        recommended_strategy = (
            top_strategies[0]["strategy"]
            if top_strategies
            else (memory_hits[0]["strategy"] if memory_hits else "balanced-execution")
        )

        analysis = {
            "goal": goal,
            "context": goal_pack.get("context", {}),
            "memory_hits": memory_hits,
            "top_strategies": top_strategies,
            "recommended_strategy": recommended_strategy,
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
            context={"goal": goal, "action": action_name, "result": result},
        )

        evaluation = {"success": success, "reward": reward, "stored_memory": stored}
        self.event_bus.publish("evaluation.completed", evaluation)
        self.event_bus.publish("memory.recorded", stored)
        return evaluation

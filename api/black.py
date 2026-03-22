from __future__ import annotations

from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.performance_comparison_engine import PerformanceComparisonEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.loop.autonomous_loop import AutonomousLoop
from core.memory.faiss_memory import FaissMemory
from core.runtime_engine import RuntimeEngine
from executor.runner import ExecutorRunner


def build_black_origin(memory_dir: str = ".black_memory"):
    event_bus = EventBus()
    runtime_engine = RuntimeEngine(event_bus=event_bus)
    memory = FaissMemory(storage_dir=memory_dir)
    task_intelligence_engine = TaskIntelligenceEngine(event_bus=event_bus, memory=memory)
    performance_engine = PerformanceComparisonEngine(event_bus=event_bus)
    goal_engine = GoalGenerationEngine(event_bus=event_bus)
    agent_system = AgentSystem(event_bus=event_bus)
    executor_runner = ExecutorRunner(event_bus=event_bus)
    autonomous_loop = AutonomousLoop(
        runtime_engine=runtime_engine,
        goal_engine=goal_engine,
        task_intelligence_engine=task_intelligence_engine,
        performance_engine=performance_engine,
        agent_system=agent_system,
        executor_runner=executor_runner,
        event_bus=event_bus,
    )

    return {
        "event_bus": event_bus,
        "runtime_engine": runtime_engine,
        "memory": memory,
        "task_intelligence_engine": task_intelligence_engine,
        "performance_engine": performance_engine,
        "goal_engine": goal_engine,
        "agent_system": agent_system,
        "executor_runner": executor_runner,
        "autonomous_loop": autonomous_loop,
    }

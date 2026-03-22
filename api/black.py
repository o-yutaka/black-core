from __future__ import annotations

from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.goal_generation_engine import GoalGenerationEngine
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine
from core.knowledge.knowledge_router import KnowledgeRouter
from core.knowledge.local_file_collector import LocalFileCollector
from core.loop.autonomous_loop import AutonomousLoop
from core.memory.api_memory import APIMemoryStorage
from core.memory.faiss_memory import FaissMemory
from core.runtime_engine import RuntimeEngine
from executor.runner import ExecutorRunner


def build_black_origin(memory_dir: str = ".black_memory"):
    event_bus = EventBus()
    runtime_engine = RuntimeEngine(event_bus=event_bus)
    memory = FaissMemory(storage_dir=memory_dir)
    api_memory = APIMemoryStorage(event_bus=event_bus, storage_dir=memory_dir)
    local_collector = LocalFileCollector(event_bus=event_bus)
    knowledge_router = KnowledgeRouter(
        event_bus=event_bus,
        faiss_memory=memory,
        api_memory=api_memory,
        local_collector=local_collector,
    )
    task_intelligence_engine = TaskIntelligenceEngine(event_bus=event_bus, memory=memory)
    goal_engine = GoalGenerationEngine(event_bus=event_bus)
    agent_system = AgentSystem(event_bus=event_bus)
    executor_runner = ExecutorRunner(event_bus=event_bus)
    autonomous_loop = AutonomousLoop(
        runtime_engine=runtime_engine,
        goal_engine=goal_engine,
        task_intelligence_engine=task_intelligence_engine,
        agent_system=agent_system,
        executor_runner=executor_runner,
        event_bus=event_bus,
        knowledge_router=knowledge_router,
        api_memory=api_memory,
    )

    return {
        "event_bus": event_bus,
        "runtime_engine": runtime_engine,
        "memory": memory,
        "api_memory": api_memory,
        "local_collector": local_collector,
        "knowledge_router": knowledge_router,
        "task_intelligence_engine": task_intelligence_engine,
        "goal_engine": goal_engine,
        "agent_system": agent_system,
        "executor_runner": executor_runner,
        "autonomous_loop": autonomous_loop,
    }

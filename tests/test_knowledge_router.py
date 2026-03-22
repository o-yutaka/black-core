from __future__ import annotations

from pathlib import Path

from core.event_bus import EventBus
from core.knowledge.knowledge_router import KnowledgeRouter
from core.knowledge.local_file_collector import LocalFileCollector
from core.memory.api_memory import APIMemoryStorage
from core.memory.faiss_memory import FaissMemory


def test_knowledge_router_combines_faiss_api_and_local_sources(tmp_path: Path):
    event_bus = EventBus()
    faiss_memory = FaissMemory(storage_dir=str(tmp_path / "mem"))
    api_memory = APIMemoryStorage(event_bus=event_bus, storage_dir=str(tmp_path / "mem"))
    collector = LocalFileCollector(event_bus=event_bus)

    faiss_memory.save_memory(
        text="Goal=Improve uptime; Action=restart-service; Summary=stable",
        strategy="deterministic-optimization",
        importance=0.9,
        success=True,
        reward=1.0,
        context={"goal": "Improve uptime"},
    )

    api_memory.store(
        request={"method": "GET", "url": "https://example.org/weather", "status_code": 200},
        response={"status_code": 200, "body": {"ok": True}},
        summary="Weather endpoint healthy",
    )

    knowledge_file = tmp_path / "playbook.txt"
    knowledge_file.write_text("Always prefer retries with bounded backoff.", encoding="utf-8")

    router = KnowledgeRouter(
        event_bus=event_bus,
        faiss_memory=faiss_memory,
        api_memory=api_memory,
        local_collector=collector,
    )

    result = router.route(
        {
            "goal": "Improve uptime in production",
            "context": {
                "api_request": {"url": "https://example.org/weather"},
                "knowledge_paths": [str(knowledge_file)],
            },
        }
    )

    assert len(result["faiss_hits"]) == 1
    assert len(result["api_hits"]) == 1
    assert len(result["local_documents"]) == 1
    assert {item["source"] for item in result["ranked_knowledge"]} == {"faiss", "api_memory", "local_file"}

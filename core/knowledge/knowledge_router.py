from __future__ import annotations

from typing import Any, Dict, List

from core.event_bus import EventBus
from core.knowledge.local_file_collector import LocalFileCollector
from core.memory.api_memory import APIMemoryStorage
from core.memory.faiss_memory import FaissMemory


class KnowledgeRouter:
    """Routes and merges knowledge from FAISS memory, API memory, and local files."""

    def __init__(
        self,
        event_bus: EventBus,
        faiss_memory: FaissMemory,
        api_memory: APIMemoryStorage,
        local_collector: LocalFileCollector,
    ) -> None:
        self.event_bus = event_bus
        self.faiss_memory = faiss_memory
        self.api_memory = api_memory
        self.local_collector = local_collector

    def route(self, goal_pack: Dict[str, Any]) -> Dict[str, Any]:
        goal = goal_pack.get("goal", "")
        context = goal_pack.get("context", {})

        faiss_hits = self.faiss_memory.search_memory(goal, top_k=5)

        api_request = context.get("api_request", {}) if isinstance(context, dict) else {}
        api_url = api_request.get("url", "") if isinstance(api_request, dict) else ""
        api_hits = self.api_memory.query(url_contains=api_url, top_k=5) if api_url else self.api_memory.query(top_k=3)

        knowledge_paths = context.get("knowledge_paths", []) if isinstance(context, dict) else []
        local_docs = self.local_collector.collect(knowledge_paths if isinstance(knowledge_paths, list) else [])

        ranked: List[Dict[str, Any]] = []
        for hit in faiss_hits:
            ranked.append({"source": "faiss", "score": float(hit.get("weighted_score", 0.0)), "item": hit})
        for row in api_hits:
            status_code = int(row.get("response", {}).get("status_code", row.get("request", {}).get("status_code", 0)))
            score = 1.0 if 200 <= status_code < 300 else 0.35
            ranked.append({"source": "api_memory", "score": score, "item": row})
        for doc in local_docs:
            score = min(1.0, 0.2 + (len(doc.get("content", "")) / 4000.0))
            ranked.append({"source": "local_file", "score": score, "item": doc})

        ranked.sort(key=lambda x: x["score"], reverse=True)
        summary = {
            "goal": goal,
            "faiss_hits": faiss_hits,
            "api_hits": api_hits,
            "local_documents": local_docs,
            "ranked_knowledge": ranked[:10],
        }
        self.event_bus.publish(
            "knowledge.routed",
            {
                "goal": goal,
                "faiss_hits": len(faiss_hits),
                "api_hits": len(api_hits),
                "local_documents": len(local_docs),
            },
        )
        return summary

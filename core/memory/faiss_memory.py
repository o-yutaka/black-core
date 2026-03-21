#!/usr/bin/env python3
from __future__ import annotations

import json
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

import numpy as np
from sentence_transformers import SentenceTransformer

try:
    import faiss  # type: ignore
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    faiss = None


@dataclass
class MemoryRecord:
    text: str
    strategy: str
    importance: float
    success: bool
    reward: float
    context: Dict[str, Any]


class FaissMemory:
    """Persistent semantic memory using sentence-transformers + FAISS."""

    def __init__(self, storage_dir: str = ".black_memory", model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)

        self.index_path = self.storage / "memory.index"
        self.meta_path = self.storage / "memory_meta.json"

        self.model = SentenceTransformer(model_name)
        self.dimension = self.model.get_sentence_embedding_dimension()
        self.index = self._load_index()
        self.metadata = self._load_metadata()
        self._fallback_vectors: List[np.ndarray] = []
        if self.index is None and self.metadata:
            for row in self.metadata:
                self._fallback_vectors.append(self._embed(row["text"])[0])

    def _load_index(self):
        if faiss is None:
            return None
        if self.index_path.exists():
            return faiss.read_index(str(self.index_path))
        return faiss.IndexFlatIP(self.dimension)

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return []

    def _save(self) -> None:
        if faiss is not None and self.index is not None:
            faiss.write_index(self.index, str(self.index_path))
        self.meta_path.write_text(json.dumps(self.metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    def _embed(self, text: str) -> np.ndarray:
        vector = self.model.encode([text], normalize_embeddings=True)
        return np.asarray(vector, dtype="float32")

    def save_memory(
        self,
        text: str,
        strategy: str,
        importance: float,
        success: bool,
        reward: float,
        context: Optional[Dict[str, Any]] = None,
    ) -> Dict[str, Any]:
        record = MemoryRecord(
            text=text,
            strategy=strategy,
            importance=float(max(0.0, min(1.0, importance))),
            success=bool(success),
            reward=float(reward),
            context=context or {},
        )

        vector = self._embed(record.text)
        if self.index is not None:
            self.index.add(vector)
        else:
            self._fallback_vectors.append(vector[0])

        saved = {
            "id": len(self.metadata),
            "text": record.text,
            "strategy": record.strategy,
            "importance": record.importance,
            "success": record.success,
            "reward": record.reward,
            "context": record.context,
            "created_at": datetime.now(timezone.utc).isoformat(),
        }
        self.metadata.append(saved)
        self._save()
        return saved

    def search_memory(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        if self.index is None and not self._fallback_vectors:
            return []
        if self.index is not None and self.index.ntotal == 0:
            return []

        vector = self._embed(query)
        if self.index is not None:
            similarities, indices = self.index.search(vector, top_k)
        else:
            matrix = np.vstack(self._fallback_vectors) if self._fallback_vectors else np.empty((0, self.dimension))
            sims = matrix @ vector[0]
            order = np.argsort(-sims)[:top_k]
            similarities = np.array([sims[order]], dtype="float32")
            indices = np.array([order], dtype="int64")

        ranked: List[Dict[str, Any]] = []
        for similarity, idx in zip(similarities[0], indices[0]):
            if idx < 0 or idx >= len(self.metadata):
                continue

            item = self.metadata[idx]
            strategy_rate = self._strategy_success_rate(item["strategy"])
            weighted = (0.55 * float(similarity)) + (0.25 * float(item["importance"])) + (0.20 * strategy_rate)

            ranked.append(
                {
                    **item,
                    "similarity": float(similarity),
                    "strategy_success_rate": strategy_rate,
                    "weighted_score": weighted,
                }
            )

        ranked.sort(key=lambda x: x["weighted_score"], reverse=True)
        return ranked

    def _strategy_success_rate(self, strategy: str) -> float:
        candidates = [m for m in self.metadata if m.get("strategy") == strategy]
        if not candidates:
            return 0.5
        wins = sum(1 for c in candidates if c.get("success"))
        return wins / len(candidates)

    def top_strategies(self, top_k: int = 3) -> List[Dict[str, Any]]:
        grouped: Dict[str, Dict[str, float]] = {}
        for row in self.metadata:
            strategy = row.get("strategy", "default")
            grouped.setdefault(strategy, {"count": 0.0, "wins": 0.0, "reward": 0.0})
            grouped[strategy]["count"] += 1
            grouped[strategy]["wins"] += 1 if row.get("success") else 0
            grouped[strategy]["reward"] += float(row.get("reward", 0.0))

        results = []
        for strategy, data in grouped.items():
            count = data["count"] or 1.0
            win_rate = data["wins"] / count
            avg_reward = data["reward"] / count
            score = 0.7 * win_rate + 0.3 * max(0.0, avg_reward)
            results.append(
                {
                    "strategy": strategy,
                    "count": int(count),
                    "win_rate": win_rate,
                    "avg_reward": avg_reward,
                    "score": score,
                }
            )

        results.sort(key=lambda x: x["score"], reverse=True)
        return results[:top_k]

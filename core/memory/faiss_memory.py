#!/usr/bin/env python3
from __future__ import annotations

import json
import math
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Dict, List, Optional

try:  # pragma: no cover - optional optimization dependency
    import numpy as np
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    np = None

try:  # pragma: no cover - optional embedding dependency
    from sentence_transformers import SentenceTransformer
except ModuleNotFoundError:  # pragma: no cover - environment-dependent
    SentenceTransformer = None  # type: ignore[misc,assignment]

try:  # pragma: no cover - optional index dependency
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
    """Persistent memory with optional FAISS/vector backends and pure-Python fallback."""

    def __init__(self, storage_dir: str = ".black_memory", model_name: str = "sentence-transformers/all-MiniLM-L6-v2"):
        self.storage = Path(storage_dir)
        self.storage.mkdir(parents=True, exist_ok=True)

        self.index_path = self.storage / "memory.index"
        self.meta_path = self.storage / "memory_meta.json"

        self.dimension = 64
        self.model = None
        if SentenceTransformer is not None and np is not None:
            try:
                self.model = SentenceTransformer(model_name)
                self.dimension = int(self.model.get_sentence_embedding_dimension())
            except Exception:
                self.model = None

        self.metadata = self._load_metadata()
        self.index = self._load_index()
        self._fallback_vectors: List[List[float]] = []
        for row in self.metadata:
            self._fallback_vectors.append(self._embed(row["text"]))

    def _load_index(self):
        if faiss is None or np is None:
            return None
        if self.index_path.exists():
            try:
                return faiss.read_index(str(self.index_path))
            except Exception:
                return faiss.IndexFlatIP(self.dimension)
        return faiss.IndexFlatIP(self.dimension)

    def _load_metadata(self) -> List[Dict[str, Any]]:
        if self.meta_path.exists():
            return json.loads(self.meta_path.read_text(encoding="utf-8"))
        return []

    def _save(self) -> None:
        if faiss is not None and np is not None and self.index is not None:
            try:
                faiss.write_index(self.index, str(self.index_path))
            except Exception:
                pass
        self.meta_path.write_text(json.dumps(self.metadata, indent=2, ensure_ascii=False), encoding="utf-8")

    def _embed(self, text: str) -> List[float]:
        if self.model is not None and np is not None:
            vector = self.model.encode([text], normalize_embeddings=True)
            return list(np.asarray(vector, dtype="float32")[0])

        values = [0.0] * self.dimension
        tokens = text.lower().split()
        if not tokens:
            return values
        for token in tokens:
            idx = hash(token) % self.dimension
            values[idx] += 1.0
        norm = math.sqrt(sum(v * v for v in values)) or 1.0
        return [v / norm for v in values]

    @staticmethod
    def _dot(left: List[float], right: List[float]) -> float:
        return float(sum(a * b for a, b in zip(left, right)))

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
        if self.index is not None and np is not None:
            self.index.add(np.asarray([vector], dtype="float32"))
        self._fallback_vectors.append(vector)

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
        if not self._fallback_vectors:
            return []

        query_vector = self._embed(query)
        scored_rows: List[Dict[str, Any]] = []
        for idx, vector in enumerate(self._fallback_vectors):
            if idx >= len(self.metadata):
                continue
            similarity = self._dot(query_vector, vector)
            item = self.metadata[idx]
            strategy_rate = self._strategy_success_rate(item["strategy"])
            weighted = (0.55 * float(similarity)) + (0.25 * float(item["importance"])) + (0.20 * strategy_rate)
            scored_rows.append(
                {
                    **item,
                    "similarity": float(similarity),
                    "strategy_success_rate": strategy_rate,
                    "weighted_score": weighted,
                }
            )

        scored_rows.sort(key=lambda x: x["weighted_score"], reverse=True)
        return scored_rows[:top_k]

    def _strategy_success_rate(self, strategy: str) -> float:
        candidates = [m for m in self.metadata if m.get("strategy") == strategy]
        if not candidates:
            return 0.5
        wins = sum(1 for c in candidates if c.get("success"))
        return wins / len(candidates)

    def failed_strategies(self, top_k: int = 5) -> List[str]:
        failed_counts: Dict[str, int] = {}
        for row in self.metadata:
            if row.get("success"):
                continue
            strategy = row.get("strategy", "default")
            failed_counts[strategy] = failed_counts.get(strategy, 0) + 1

        ranked = sorted(failed_counts.items(), key=lambda item: item[1], reverse=True)
        return [strategy for strategy, _ in ranked[:top_k]]

    def best_practices(self, top_k: int = 5) -> List[Dict[str, Any]]:
        successful = [row for row in self.metadata if row.get("success")]
        successful.sort(key=lambda row: (float(row.get("importance", 0.0)), float(row.get("reward", 0.0))), reverse=True)
        return successful[:top_k]

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

from __future__ import annotations

import random
from typing import Any, Dict, List


class ContentOptimizer:
    def __init__(self) -> None:
        self.topics = [
            "AI automation",
            "creator monetization",
            "audience growth",
            "digital product funnels",
            "high-leverage workflows",
        ]

    def choose_topic(self, memory: Dict[str, Any]) -> str:
        posts = memory.get("posts", [])
        if not posts:
            return random.choice(self.topics)

        best = sorted(posts, key=lambda x: x.get("score", 0), reverse=True)[:10]
        topic_scores: Dict[str, List[float]] = {}
        for post in best:
            topic = post.get("topic", random.choice(self.topics))
            topic_scores.setdefault(topic, []).append(post.get("score", 0.0))

        avg_scores = {topic: sum(values) / len(values) for topic, values in topic_scores.items()}
        ranked_topics = sorted(avg_scores, key=avg_scores.get, reverse=True)

        if ranked_topics and random.random() < 0.8:
            return ranked_topics[0]
        return random.choice(self.topics)

    def mutation_guidance(self, memory: Dict[str, Any]) -> Dict[str, Any]:
        posts = sorted(memory.get("posts", []), key=lambda p: p.get("score", 0), reverse=True)[:5]
        if not posts:
            return {
                "instruction": "Use hook + mechanism + concise CTA bridge.",
                "source_examples": [],
            }

        examples = [p.get("content", "") for p in posts]
        return {
            "instruction": "Reuse top hook structure, change mechanism detail, vary opening phrase and close with urgency.",
            "source_examples": examples,
        }

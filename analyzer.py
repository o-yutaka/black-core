from __future__ import annotations

from typing import Any, Dict, List


class PerformanceAnalyzer:
    def __init__(self, click_weight: float = 3.0) -> None:
        self.click_weight = click_weight

    def score(self, likes: int, clicks: int) -> float:
        return float(likes + (clicks * self.click_weight))

    def top_posts(self, posts: List[Dict[str, Any]], limit: int = 5) -> List[Dict[str, Any]]:
        ranked = sorted(posts, key=lambda p: p.get("score", 0.0), reverse=True)
        return ranked[:limit]

    def summarize_patterns(self, posts: List[Dict[str, Any]]) -> Dict[str, Any]:
        if not posts:
            return {
                "avg_length": 0,
                "question_rate": 0.0,
                "hashtag_rate": 0.0,
                "keyword_hits": {},
            }

        total = len(posts)
        keyword_hits: Dict[str, int] = {}
        keywords = ["system", "framework", "template", "playbook", "mistake", "secret", "automation"]

        for post in posts:
            text = post.get("content", "").lower()
            for keyword in keywords:
                if keyword in text:
                    keyword_hits[keyword] = keyword_hits.get(keyword, 0) + 1

        return {
            "avg_length": int(sum(len(p.get("content", "")) for p in posts) / total),
            "question_rate": sum("?" in p.get("content", "") for p in posts) / total,
            "hashtag_rate": sum("#" in p.get("content", "") for p in posts) / total,
            "keyword_hits": keyword_hits,
        }

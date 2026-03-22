from __future__ import annotations

import json
import os
import time
from pathlib import Path
from typing import Any, Dict

from analyzer import PerformanceAnalyzer
from api.black import build_black_origin
from executor import MockXExecutor
from generator import ContentGenerator
from monetization import MonetizationEngine
from optimizer import ContentOptimizer


class SNSAutonomousMonetizationSystem:
    def __init__(self, memory_path: str = "memory.json", interval_seconds: int = 3600) -> None:
        self.memory_path = Path(memory_path)
        self.interval_seconds = interval_seconds

        system = build_black_origin()
        self.event_bus = system["event_bus"]
        self.runtime_engine = system["runtime_engine"]

        self.generator = ContentGenerator(memory_path=memory_path)
        self.executor = MockXExecutor()
        self.analyzer = PerformanceAnalyzer(click_weight=3.0)
        self.optimizer = ContentOptimizer()
        self.monetization = MonetizationEngine(link=os.getenv("MONETIZATION_LINK", "https://example.com/offer"))

        self._subscribe_events()
        self._ensure_memory_file()

    def _subscribe_events(self) -> None:
        self.event_bus.subscribe("monetization.post.generated", lambda payload: None)
        self.event_bus.subscribe("monetization.post.executed", lambda payload: None)
        self.event_bus.subscribe("monetization.loop.completed", lambda payload: None)

    def _ensure_memory_file(self) -> None:
        if not self.memory_path.exists():
            self.memory_path.write_text(json.dumps({"posts": [], "cta_stats": {}}, indent=2), encoding="utf-8")

    def _load_memory(self) -> Dict[str, Any]:
        return json.loads(self.memory_path.read_text(encoding="utf-8"))

    def _save_memory(self, memory: Dict[str, Any]) -> None:
        self.memory_path.write_text(json.dumps(memory, indent=2), encoding="utf-8")

    def run_cycle(self) -> Dict[str, Any]:
        memory = self._load_memory()
        topic = self.optimizer.choose_topic(memory)
        top_posts = self.analyzer.top_posts(memory.get("posts", []), limit=5)
        mutation = self.optimizer.mutation_guidance(memory)

        generation = self.generator.generate(topic=topic, top_posts=top_posts)
        raw_content = generation["content"]
        if mutation["source_examples"]:
            raw_content = f"{raw_content}"

        cta_choice = self.monetization.select_cta(memory)
        post_content = self.monetization.inject_cta(raw_content, cta_choice)

        self.event_bus.publish(
            "monetization.post.generated",
            {
                "topic": topic,
                "content": post_content,
                "cta_variant": cta_choice.variant,
                "style_hints": generation["style_hints"],
            },
        )

        posted = self.executor.post(post_content)
        score = self.analyzer.score(posted.likes, posted.clicks)

        self.monetization.update_cta_performance(memory, cta_choice.variant, posted.clicks)
        memory.setdefault("posts", []).append(
            {
                "post_id": posted.post_id,
                "posted_at": posted.posted_at,
                "topic": topic,
                "content": post_content,
                "cta_variant": cta_choice.variant,
                "likes": posted.likes,
                "clicks": posted.clicks,
                "score": score,
                "weight": self.analyzer.click_weight,
            }
        )

        top_after = self.analyzer.top_posts(memory["posts"], limit=5)
        patterns = self.analyzer.summarize_patterns(top_after)
        memory["learning"] = {
            "top_patterns": patterns,
            "best_topics": [p.get("topic", "") for p in top_after],
        }

        self._save_memory(memory)

        result = {
            "topic": topic,
            "post_id": posted.post_id,
            "likes": posted.likes,
            "clicks": posted.clicks,
            "score": score,
            "cta_variant": cta_choice.variant,
            "top_patterns": patterns,
        }

        self.event_bus.publish("monetization.post.executed", result)
        self.event_bus.publish("monetization.loop.completed", result)
        return result

    def run_forever(self) -> None:
        self.runtime_engine.start()
        try:
            while True:
                runtime_state = {
                    "goal": "maximize_sns_revenue",
                    "subsystem": "sns_monetization",
                    "memory_file": str(self.memory_path),
                }
                self.runtime_engine.tick(runtime_state)
                self.run_cycle()
                time.sleep(self.interval_seconds)
        finally:
            self.runtime_engine.stop("sns_scheduler_shutdown")


if __name__ == "__main__":
    interval = int(os.getenv("SNS_INTERVAL_SECONDS", "3600"))
    system = SNSAutonomousMonetizationSystem(interval_seconds=interval)
    system.run_forever()

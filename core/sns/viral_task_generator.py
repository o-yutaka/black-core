from __future__ import annotations

from typing import Any, Dict, List


class ViralTaskGenerator:
    def generate(self, goal: str, signals: List[Dict[str, Any]], max_tasks: int = 3) -> List[Dict[str, Any]]:
        tasks: List[Dict[str, Any]] = []
        for signal in signals[:max_tasks]:
            topic = signal["topic"]
            tasks.append(
                {
                    "topic": topic,
                    "source": signal["source"],
                    "hook": f"{topic}: what creators are missing right now",
                    "script": self._build_script(goal=goal, topic=topic),
                    "virality_score": signal["virality_score"],
                }
            )
        return tasks

    @staticmethod
    def _build_script(goal: str, topic: str) -> str:
        return (
            f"Goal: {goal}.\n"
            f"1) Lead with a contrarian claim on {topic}.\n"
            f"2) Deliver one practical monetization tactic.\n"
            "3) End with a clear CTA to the affiliate link."
        )

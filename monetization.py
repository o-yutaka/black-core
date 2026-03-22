from __future__ import annotations

import math
from dataclasses import dataclass
from typing import Any, Dict, List


DEFAULT_CTAS = [
    "Get the full playbook here: {link}",
    "Steal the exact system: {link}",
    "See the step-by-step template: {link}",
    "Download the growth checklist: {link}",
]


@dataclass
class CTASelection:
    variant: str
    rendered: str


class MonetizationEngine:
    def __init__(self, link: str = "https://example.com/offer") -> None:
        self.link = link

    def select_cta(self, memory: Dict[str, Any]) -> CTASelection:
        cta_stats = memory.setdefault("cta_stats", {})
        for variant in DEFAULT_CTAS:
            cta_stats.setdefault(variant, {"impressions": 0, "clicks": 0})

        total_impressions = sum(stats["impressions"] for stats in cta_stats.values()) + 1

        def ucb(variant: str) -> float:
            stats = cta_stats[variant]
            impressions = stats["impressions"]
            clicks = stats["clicks"]
            if impressions == 0:
                return float("inf")
            ctr = clicks / impressions
            return ctr + math.sqrt((2 * math.log(total_impressions)) / impressions)

        best_variant = max(cta_stats.keys(), key=ucb)
        return CTASelection(variant=best_variant, rendered=best_variant.format(link=self.link))

    def inject_cta(self, content: str, cta: CTASelection) -> str:
        merged = f"{content.strip()}\n\n{cta.rendered}".strip()
        return merged[:280]

    def update_cta_performance(self, memory: Dict[str, Any], variant: str, clicks: int) -> None:
        cta_stats = memory.setdefault("cta_stats", {})
        stats = cta_stats.setdefault(variant, {"impressions": 0, "clicks": 0})
        stats["impressions"] += 1
        stats["clicks"] += max(0, clicks)


if __name__ == "__main__":
    sample_memory: Dict[str, Any] = {"posts": [], "cta_stats": {}}
    engine = MonetizationEngine()
    cta = engine.select_cta(sample_memory)
    print(engine.inject_cta("Your audience is one idea away from conversion.", cta))

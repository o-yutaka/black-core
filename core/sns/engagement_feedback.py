from __future__ import annotations

from typing import Any, Dict, List


class EngagementFeedback:
    def summarize(self, posts: List[Dict[str, Any]]) -> Dict[str, float]:
        if not posts:
            return {"engagement_rate": 0.0, "conversion_rate": 0.0, "revenue_per_post": 0.0}

        impressions = sum(float(p.get("impressions", 0.0)) for p in posts)
        engagements = sum(float(p.get("engagements", 0.0)) for p in posts)
        clicks = sum(float(p.get("clicks", 0.0)) for p in posts)
        conversions = sum(float(p.get("conversions", 0.0)) for p in posts)
        revenue = sum(float(p.get("revenue", 0.0)) for p in posts)

        return {
            "engagement_rate": (engagements / impressions) if impressions else 0.0,
            "conversion_rate": (conversions / clicks) if clicks else 0.0,
            "revenue_per_post": revenue / len(posts),
        }

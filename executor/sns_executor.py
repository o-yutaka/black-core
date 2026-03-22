from __future__ import annotations

from typing import Any, Dict, List

from core.sns.engagement_feedback import EngagementFeedback


class SNSExecutor:
    def __init__(self) -> None:
        self.feedback = EngagementFeedback()

    def execute_campaign(self, task: Dict[str, Any]) -> Dict[str, Any]:
        posts = task.get("posts", [])
        simulated_posts = [self._simulate_post(row) for row in posts]
        metrics = self.feedback.summarize(simulated_posts)
        total_revenue = sum(row["revenue"] for row in simulated_posts)

        success = total_revenue > 0
        return {
            "success": success,
            "stdout": "",
            "stderr": "",
            "return_code": 0 if success else 1,
            "timed_out": False,
            "summary": "sns_campaign_executed" if success else "sns_campaign_no_revenue",
            "reward": min(2.0, total_revenue / 100.0),
            "engagement": {
                "posts": simulated_posts,
                "aggregate": metrics,
                "revenue": total_revenue,
            },
        }

    def _simulate_post(self, post: Dict[str, Any]) -> Dict[str, Any]:
        virality = float(post.get("virality_score", 0.0))
        hour = int(post.get("scheduled_hour_utc", 12))
        timing_multiplier = 1.2 if hour in {14, 16, 19, 22} else 0.9

        impressions = max(100.0, 1200.0 * virality * timing_multiplier)
        engagements = impressions * min(0.3, 0.05 + (virality * 0.08))
        clicks = engagements * 0.2
        conversions = clicks * 0.08
        revenue = conversions * 18.0

        return {
            **post,
            "impressions": round(impressions, 2),
            "engagements": round(engagements, 2),
            "clicks": round(clicks, 2),
            "conversions": round(conversions, 2),
            "revenue": round(revenue, 2),
        }

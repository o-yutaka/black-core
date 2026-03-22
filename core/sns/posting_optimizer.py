from __future__ import annotations

from datetime import datetime, timezone
from typing import Dict, List


class PostingTimingOptimizer:
    """Simple deterministic optimizer using historical engagement by hour."""

    def optimize(self, tasks: List[Dict[str, object]], engagement_history: List[Dict[str, object]]) -> List[Dict[str, object]]:
        ranked_hours = self._rank_hours(engagement_history)
        scheduled: List[Dict[str, object]] = []

        for idx, task in enumerate(tasks):
            hour = ranked_hours[idx % len(ranked_hours)]
            scheduled.append({**task, "scheduled_hour_utc": hour})
        return scheduled

    def _rank_hours(self, history: List[Dict[str, object]]) -> List[int]:
        buckets = {hour: {"engagement": 0.0, "count": 0} for hour in range(24)}
        for row in history:
            try:
                posted_at = datetime.fromisoformat(str(row.get("posted_at"))).astimezone(timezone.utc)
                hour = posted_at.hour
            except Exception:
                continue
            buckets[hour]["engagement"] += float(row.get("engagement", 0.0))
            buckets[hour]["count"] += 1

        if all(meta["count"] == 0 for meta in buckets.values()):
            return [14, 16, 19, 22]

        ranking = sorted(
            range(24),
            key=lambda hour: (buckets[hour]["engagement"] / buckets[hour]["count"]) if buckets[hour]["count"] else -1,
            reverse=True,
        )
        return ranking[:4]

from __future__ import annotations

import hashlib
import random
import time
from dataclasses import dataclass
from datetime import datetime, timezone


@dataclass
class PostResult:
    post_id: str
    posted_at: str
    likes: int
    clicks: int


class MockXExecutor:
    def __init__(self, seed: int | None = None) -> None:
        self.rng = random.Random(seed)

    def post(self, content: str) -> PostResult:
        post_id = hashlib.sha1(f"{content}-{time.time()}".encode("utf-8")).hexdigest()[:12]
        quality = self._estimate_quality(content)
        likes = max(0, int(self.rng.gauss(quality * 36, 12)))
        clicks = max(0, int(self.rng.gauss(quality * 8, 4)))
        return PostResult(
            post_id=post_id,
            posted_at=datetime.now(timezone.utc).isoformat(),
            likes=likes,
            clicks=clicks,
        )

    def _estimate_quality(self, content: str) -> float:
        score = 1.0
        length = len(content)
        if 120 <= length <= 260:
            score += 0.45
        if "?" in content:
            score += 0.2
        if "#" in content:
            score += 0.15
        if "http" in content:
            score += 0.2
        if any(token in content.lower() for token in ("system", "framework", "template", "playbook", "secret")):
            score += 0.25
        return score


if __name__ == "__main__":
    ex = MockXExecutor(seed=42)
    res = ex.post("Build once, distribute forever. Get the system: https://example.com")
    print(res)

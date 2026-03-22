#!/usr/bin/env python3
from __future__ import annotations

import json

from api.black import build_black_origin


def main() -> None:
    system = build_black_origin()
    runtime = system["runtime_engine"]
    loop = system["autonomous_loop"]
    scheduler = system["persistent_scheduler"]

    runtime.start()
    summary = loop.run_once(
        {
            "goal": "Increase autonomous task completion reliability",
            "environment": "production",
            "target": "profit_optimization",
            "data_sources": [
                {"name": "hn-front-page", "type": "web", "url": "https://news.ycombinator.com/"},
                {"name": "coindesk-api", "type": "api", "url": "https://api.coindesk.com/v1/bpi/currentprice.json"},
            ],
            "output_channels": [{"type": "file", "path": ".black_memory/autonomy_feed.jsonl"}, {"type": "api"}],
        }
    )

    scheduler.register_job(
        name="hourly-growth-loop",
        interval_seconds=3600,
        payload={
            "goal": "Generate new monetization opportunities",
            "environment": "production",
            "target": "revenue_growth",
            "output_channels": [{"type": "file", "path": ".black_memory/autonomy_feed.jsonl"}],
        },
    )

    runtime.stop("single-cycle-complete")

    print(
        json.dumps(
            {
                "cycle": summary["snapshot"]["cycle"],
                "strategy": summary["arena_plan"]["strategy"],
                "success": summary["action_result"]["success"],
                "reward": summary["action_result"]["reward"],
                "projected_revenue": summary["monetization_plan"]["projected_revenue"],
                "ingested_signals": summary["ingestion_report"]["signal_count"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

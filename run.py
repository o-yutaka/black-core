#!/usr/bin/env python3
from __future__ import annotations

import json

from api.black import build_black_origin


def main() -> None:
    system = build_black_origin()
    runtime = system["runtime_engine"]
    loop = system["autonomous_loop"]

    runtime.start()
    summary = loop.run_once(
        {
            "goal": "Increase autonomous task completion reliability",
            "environment": "production",
            "target": "profit_optimization",
        }
    )
    runtime.stop("single-cycle-complete")

    print(
        json.dumps(
            {
                "cycle": summary["snapshot"]["cycle"],
                "strategy": summary["arena_plan"]["strategy"],
                "success": summary["action_result"]["success"],
                "reward": summary["action_result"]["reward"],
                "stdout": summary["action_result"]["stdout"],
                "stderr": summary["action_result"]["stderr"],
            },
            indent=2,
        )
    )


if __name__ == "__main__":
    main()

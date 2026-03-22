from __future__ import annotations

from typing import Dict, List
from urllib.parse import urlencode


class CTALinkEngine:
    def attach(self, tasks: List[Dict[str, object]], base_url: str, campaign: str, source: str = "black-origin") -> List[Dict[str, object]]:
        enriched: List[Dict[str, object]] = []
        for task in tasks:
            topic = str(task.get("topic", "general"))
            params = {
                "utm_source": source,
                "utm_campaign": campaign,
                "utm_content": topic.replace(" ", "-").lower(),
            }
            separator = "&" if "?" in base_url else "?"
            affiliate_url = f"{base_url}{separator}{urlencode(params)}"

            enriched.append({**task, "cta": f"Get the resource here: {affiliate_url}", "affiliate_url": affiliate_url})
        return enriched

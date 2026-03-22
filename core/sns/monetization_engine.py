from __future__ import annotations

from typing import Any, Dict

from core.event_bus import EventBus
from core.sns.cta_link_engine import CTALinkEngine
from core.sns.posting_optimizer import PostingTimingOptimizer
from core.sns.social_data_ingestion import SocialDataIngestion
from core.sns.viral_task_generator import ViralTaskGenerator


class SNSMonetizationEngine:
    def __init__(self, event_bus: EventBus) -> None:
        self.event_bus = event_bus
        self.ingestion = SocialDataIngestion(event_bus=event_bus)
        self.task_generator = ViralTaskGenerator()
        self.cta_engine = CTALinkEngine()
        self.timing_optimizer = PostingTimingOptimizer()

    def build_campaign(self, goal: str, context: Dict[str, Any]) -> Dict[str, Any]:
        signals = self.ingestion.ingest(context)
        tasks = self.task_generator.generate(goal=goal, signals=signals)

        sns_context = context.get("sns", {})
        affiliate_base_url = str(sns_context.get("affiliate_base_url", "https://example.com/offer"))
        campaign_name = str(sns_context.get("campaign_name", "black-origin-sns"))
        engagement_history = sns_context.get("engagement_history", [])

        with_cta = self.cta_engine.attach(tasks=tasks, base_url=affiliate_base_url, campaign=campaign_name)
        scheduled = self.timing_optimizer.optimize(tasks=with_cta, engagement_history=engagement_history)

        campaign = {
            "goal": goal,
            "signals": signals,
            "posts": scheduled,
            "affiliate_base_url": affiliate_base_url,
            "campaign_name": campaign_name,
        }
        self.event_bus.publish("sns.campaign.generated", campaign)
        return campaign

from __future__ import annotations

from api.black import build_black_origin
from core.agents.agent_system import AgentSystem
from core.event_bus import EventBus
from core.intelligence.task_intelligence_engine import TaskIntelligenceEngine


class FakeMemory:
    def search_memory(self, query: str, top_k: int = 5):
        return []

    def top_strategies(self, top_k: int = 3):
        return []

    def failed_strategies(self, top_k: int = 5):
        return []

    def best_practices(self, top_k: int = 3):
        return []

    def save_memory(self, **kwargs):
        return kwargs


def test_agent_system_builds_sns_task_when_campaign_is_present():
    system = AgentSystem(event_bus=EventBus())

    analysis = {
        "goal": "Monetize creator audience",
        "context": {
            "sns_campaign": {
                "campaign_name": "march-launch",
                "signals": [{"topic": "ai tools"}],
                "posts": [{"topic": "ai tools", "virality_score": 1.2}],
            }
        },
        "memory_hits": [],
        "top_strategies": [{"strategy": "deterministic-optimization", "win_rate": 0.7}],
        "failed_strategies": [],
    }

    plan = system.plan(analysis)
    task = plan["tasks"][0]

    assert task["type"] == "sns_campaign"
    assert task["name"] == "execute-sns-monetization"
    assert task["campaign_name"] == "march-launch"


def test_full_loop_generates_campaign_executes_and_records_engagement(tmp_path):
    system = build_black_origin(memory_dir=str(tmp_path / ".memory"))
    runtime = system["runtime_engine"]
    loop = system["autonomous_loop"]

    runtime.start()
    summary = loop.run_once(
        {
            "goal": "Grow SNS affiliate revenue",
            "sns": {
                "campaign_name": "affiliate-sprint",
                "affiliate_base_url": "https://example.com/deal",
                "x_trends": [{"topic": "AI side hustle", "engagement": 0.8, "velocity": 0.7, "sentiment": 0.4}],
                "reddit_trends": [{"topic": "Automation workflows", "engagement": 0.9, "velocity": 0.8, "sentiment": 0.5}],
                "engagement_history": [
                    {"posted_at": "2026-03-20T14:00:00+00:00", "engagement": 520},
                    {"posted_at": "2026-03-20T19:00:00+00:00", "engagement": 700},
                ],
            },
        }
    )
    runtime.stop("test-complete")

    assert summary["sns_campaign"]["campaign_name"] == "affiliate-sprint"
    assert summary["arena_plan"]["tasks"][0]["type"] == "sns_campaign"
    assert summary["action_result"]["engagement"]["revenue"] > 0
    assert "EngagementRate=" in summary["evaluation"]["stored_memory"]["text"]


def test_task_intelligence_derives_reward_from_engagement_when_missing():
    engine = TaskIntelligenceEngine(event_bus=EventBus(), memory=FakeMemory())

    evaluation = engine.evaluate_and_remember(
        goal="Monetize creator audience",
        strategy="sns-monetization",
        action_name="execute-sns-monetization",
        result={
            "success": True,
            "summary": "sns_campaign_executed",
            "engagement": {
                "revenue": 135.0,
                "aggregate": {"engagement_rate": 0.12, "conversion_rate": 0.08},
            },
        },
    )

    assert evaluation["reward"] == 1.35

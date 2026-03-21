from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Dict, List


@dataclass
class AgentProposal:
    agent: str
    plan: Dict[str, Any]


class _BaseDeliberationAgent:
    def __init__(self, name: str) -> None:
        self.name = name

    def propose(self, goal: str, context: Dict[str, Any], memory_hints: Dict[str, Any]) -> Dict[str, Any]:
        raise NotImplementedError

    def critique(self, proposals: List[AgentProposal], goal: str) -> Dict[str, Any]:
        raise NotImplementedError


class LogicAgent(_BaseDeliberationAgent):
    def __init__(self) -> None:
        super().__init__(name="logic_agent")

    def propose(self, goal: str, context: Dict[str, Any], memory_hints: Dict[str, Any]) -> Dict[str, Any]:
        successful = memory_hints.get("successful_strategies", [])
        default_strategy = successful[0] if successful else "deterministic-optimization"
        return {
            "strategy": default_strategy,
            "algorithm": "weighted-priority-selection",
            "steps": [
                "Extract explicit target from goal and context",
                "Build weighted candidate actions",
                "Choose top action by risk-adjusted score",
                "Emit machine-readable outcome",
            ],
            "risk_controls": ["bounded loops", "strict numeric scoring"],
        }

    def critique(self, proposals: List[AgentProposal], goal: str) -> Dict[str, Any]:
        weak_points: List[str] = []
        for proposal in proposals:
            if "steps" not in proposal.plan or len(proposal.plan.get("steps", [])) < 3:
                weak_points.append(f"{proposal.agent} lacks enough executable steps")
        return {
            "agent": self.name,
            "focus": "correctness",
            "issues": weak_points,
            "recommendation": "prioritize plans with deterministic scoring and clear outputs",
        }


class CreativeAgent(_BaseDeliberationAgent):
    def __init__(self) -> None:
        super().__init__(name="creative_agent")

    def propose(self, goal: str, context: Dict[str, Any], memory_hints: Dict[str, Any]) -> Dict[str, Any]:
        failed = set(memory_hints.get("failed_strategies", []))
        strategy = "adaptive-hybrid-search" if "adaptive-hybrid-search" not in failed else "contextual-ensemble"
        return {
            "strategy": strategy,
            "algorithm": "scenario-generation-and-ranking",
            "steps": [
                "Generate multiple candidate actions from context dimensions",
                "Score each candidate by utility and novelty",
                "Blend top candidates into one robust action",
                "Produce transparent reasoning trace",
            ],
            "risk_controls": ["fallback to conservative action on ties"],
        }

    def critique(self, proposals: List[AgentProposal], goal: str) -> Dict[str, Any]:
        enhancements: List[str] = []
        for proposal in proposals:
            if proposal.plan.get("algorithm") == "weighted-priority-selection":
                enhancements.append(f"{proposal.agent} can add alternative scenarios before final scoring")
        return {
            "agent": self.name,
            "focus": "novelty",
            "issues": enhancements,
            "recommendation": "add controlled exploration before committing",
        }


class CriticalAgent(_BaseDeliberationAgent):
    def __init__(self) -> None:
        super().__init__(name="critical_agent")

    def propose(self, goal: str, context: Dict[str, Any], memory_hints: Dict[str, Any]) -> Dict[str, Any]:
        return {
            "strategy": "adversarial-validation",
            "algorithm": "stress-test-and-select",
            "steps": [
                "List assumptions from each candidate action",
                "Stress-test assumptions with failure scenarios",
                "Reject brittle actions and keep resilient one",
                "Output mitigation plan alongside result",
            ],
            "risk_controls": ["explicit failure checklist", "runtime invariant checks"],
        }

    def critique(self, proposals: List[AgentProposal], goal: str) -> Dict[str, Any]:
        issues: List[str] = []
        for proposal in proposals:
            controls = proposal.plan.get("risk_controls", [])
            if not controls:
                issues.append(f"{proposal.agent} has no risk controls")
        return {
            "agent": self.name,
            "focus": "failure-discovery",
            "issues": issues,
            "recommendation": "select plan with strongest safety constraints",
        }


class MultiAgentReasoner:
    def __init__(self) -> None:
        self.logic_agent = LogicAgent()
        self.creative_agent = CreativeAgent()
        self.critical_agent = CriticalAgent()
        self._agents: List[_BaseDeliberationAgent] = [
            self.logic_agent,
            self.creative_agent,
            self.critical_agent,
        ]

    def deliberate(self, goal: str, context: Dict[str, Any], memory_hints: Dict[str, Any]) -> Dict[str, Any]:
        proposals = [
            AgentProposal(agent=agent.name, plan=agent.propose(goal=goal, context=context, memory_hints=memory_hints))
            for agent in self._agents
        ]
        critiques = [agent.critique(proposals=proposals, goal=goal) for agent in self._agents]

        scored = []
        for proposal in proposals:
            score = self._score_plan(proposal.plan, critiques)
            scored.append({"agent": proposal.agent, "plan": proposal.plan, "score": score})

        scored.sort(key=lambda item: item["score"], reverse=True)
        winner = scored[0]
        return {
            "winner_agent": winner["agent"],
            "selected_plan": winner["plan"],
            "agent_plans": [
                {"agent": proposal.agent, "plan": proposal.plan}
                for proposal in proposals
            ],
            "discussion": critiques,
            "scoreboard": scored,
        }

    @staticmethod
    def _score_plan(plan: Dict[str, Any], critiques: List[Dict[str, Any]]) -> float:
        base = 1.0
        base += 0.4 * len(plan.get("steps", []))
        base += 0.3 * len(plan.get("risk_controls", []))
        issue_penalty = 0.0
        for critique in critiques:
            for issue in critique.get("issues", []):
                if plan.get("strategy", "") in issue:
                    issue_penalty += 0.4
                else:
                    issue_penalty += 0.15
        return base - issue_penalty

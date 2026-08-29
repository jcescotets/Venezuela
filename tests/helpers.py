"""
Shared test helpers -- factory functions for agents, contracts, and pipeline results.
Separated from conftest.py so they can be imported in test modules.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.message_bus import MessageBus
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
    VetoDecision,
)


def make_contract(
    name: str = "Test Agent",
    role: AgentRole = AgentRole.FUNDAMENTAL,
    layer: AgentLayer = AgentLayer.ANALYSIS,
    specialty: str = "Testing",
    primary_objective: str = "Test objective",
    can_veto: list[str] | None = None,
    can_recommend: list[str] | None = None,
    reports_to: list[AgentRole] | None = None,
    interacts_with: list[AgentRole] | None = None,
) -> AgentContract:
    return AgentContract(
        name=name,
        role=role,
        layer=layer,
        specialty=specialty,
        primary_objective=primary_objective,
        can_veto=can_veto or [],
        can_recommend=can_recommend or ["test recommendations"],
        inputs=["test input"],
        outputs=["test output"],
        reports_to=reports_to or [AgentRole.CIO],
        interacts_with=interacts_with or [],
    )


class ConcreteTestAgent(BaseAgent):
    """Minimal concrete agent for testing (BaseAgent is abstract)."""

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        return f"Analyze: {subject}"


def make_agent(
    name: str = "Test Agent",
    role: AgentRole = AgentRole.FUNDAMENTAL,
    layer: AgentLayer = AgentLayer.ANALYSIS,
    can_veto: list[str] | None = None,
    bus: MessageBus | None = None,
) -> ConcreteTestAgent:
    contract = make_contract(name=name, role=role, layer=layer, can_veto=can_veto)
    agent = ConcreteTestAgent(contract, bus=bus)
    return agent


def make_pipeline_result(
    proposal: InvestmentProposal,
    analysis_count: int = 3,
    fiscal_count: int = 2,
    committee: CommitteeDecision | None = None,
    vetoes: list[VetoDecision] | None = None,
    status: DecisionStatus = DecisionStatus.AWAITING_USER,
) -> dict[str, Any]:
    """Build a synthetic pipeline result dict matching DecisionPipeline output."""
    return {
        "proposal": proposal,
        "phases": {
            "analysis": {
                "count": analysis_count,
                "agents": ["fundamental", "macro_geopolitics", "technical_quant"][:analysis_count],
            },
            "fiscal": {
                "count": fiscal_count,
                "agents": ["fiscal_spain", "fiscal_us"][:fiscal_count],
            },
        },
        "vetoes": vetoes or [],
        "committee_decision": committee,
        "cio_synthesis": committee,
        "veto_check": {
            "blocked": bool(vetoes),
            "active_vetoes": vetoes or [],
            "advisory_vetoes": [],
            "veto_summary": "",
            "can_override": True,
            "override_warning": None,
        },
        "validation": {
            "valid": True,
            "checks": {
                "analyzed_by_relevant_agents": True,
                "has_financial_impact": committee is not None,
                "has_fiscal_impact": fiscal_count > 0,
                "evaluated_by_risk_manager": True,
                "passed_investment_committee": committee is not None,
            },
            "missing": [],
        },
        "status": status,
        "ready_for_principal": status == DecisionStatus.AWAITING_USER,
    }

"""
Shared fixtures for Family Office test suite.
Factory functions live in tests/helpers.py so test modules can import them.
"""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from family_office.core.message_bus import MessageBus
from family_office.core.models import (
    AgentLayer,
    AgentRole,
    AnalysisReport,
    CommitteeDecision,
    DecisionStatus,
    FiscalImpact,
    InvestmentProposal,
    Message,
    MessageType,
    PortfolioAsset,
    ScenarioAnalysis,
    VetoDecision,
    VetoType,
)
from family_office.core.registry import AgentRegistry
from family_office.memory.decision_store import DecisionStore
from family_office.memory.memory_manager import MemoryManager

from tests.helpers import make_agent, ConcreteTestAgent


# ---------------------------------------------------------------------------
# Event loop
# ---------------------------------------------------------------------------

@pytest.fixture
def event_loop():
    """Provide a fresh event loop per test (pytest-asyncio compatibility)."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# ---------------------------------------------------------------------------
# Core infrastructure fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def message_bus() -> MessageBus:
    return MessageBus()


@pytest.fixture
def registry(message_bus) -> AgentRegistry:
    return AgentRegistry(message_bus)


# ---------------------------------------------------------------------------
# Agent fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def analysis_agent(message_bus) -> ConcreteTestAgent:
    return make_agent(
        name="Fundamental Analyst",
        role=AgentRole.FUNDAMENTAL,
        layer=AgentLayer.ANALYSIS,
        bus=message_bus,
    )


@pytest.fixture
def risk_agent(message_bus) -> ConcreteTestAgent:
    return make_agent(
        name="Risk Manager",
        role=AgentRole.RISK_MANAGER,
        layer=AgentLayer.RISK,
        can_veto=["risk_drawdown", "risk_correlation", "risk_concentration"],
        bus=message_bus,
    )


@pytest.fixture
def fiscal_agent(message_bus) -> ConcreteTestAgent:
    return make_agent(
        name="Fiscal Spain",
        role=AgentRole.FISCAL_SPAIN,
        layer=AgentLayer.FISCAL,
        bus=message_bus,
    )


@pytest.fixture
def cio_agent(message_bus) -> ConcreteTestAgent:
    return make_agent(
        name="CIO",
        role=AgentRole.CIO,
        layer=AgentLayer.DIRECTION,
        bus=message_bus,
    )


# ---------------------------------------------------------------------------
# Model factory fixtures
# ---------------------------------------------------------------------------

@pytest.fixture
def sample_proposal() -> InvestmentProposal:
    return InvestmentProposal(
        title="Buy AAPL",
        asset_class="equities",
        description="Purchase Apple stock for long-term growth",
        amount_usd=500_000,
        expected_gross_return_pct=12.5,
        time_horizon_months=24,
        jurisdiction="US",
        holding_vehicle="Direct",
    )


@pytest.fixture
def sample_analysis_report() -> AnalysisReport:
    return AnalysisReport(
        agent_role=AgentRole.FUNDAMENTAL,
        subject="AAPL Analysis",
        summary="Apple shows strong fundamentals.",
        conviction_level=0.8,
        key_findings=["Revenue growth 15%", "Strong cash position"],
        risks_identified=["China exposure", "Regulatory risk"],
        recommendation="Buy with 5% portfolio allocation",
    )


@pytest.fixture
def sample_veto() -> VetoDecision:
    return VetoDecision(
        agent_role=AgentRole.RISK_MANAGER,
        proposal_id="test-proposal-123",
        veto_type=VetoType.RISK_CONCENTRATION,
        justification="Position exceeds 10% concentration limit",
        severity=0.8,
        conditions_to_lift=["Reduce position to under 10%"],
    )


@pytest.fixture
def sample_committee_decision() -> CommitteeDecision:
    return CommitteeDecision(
        proposal_id="test-proposal-123",
        agreements=["Strong fundamentals", "Reasonable valuation"],
        contradictions=["Macro risk vs sector strength"],
        scenarios=ScenarioAnalysis(
            scenario_base="10% return in 12 months",
            scenario_optimistic="18% return with strong earnings",
            scenario_adverse="-5% with recession",
            main_risks=["Macro downturn", "Multiple compression"],
            recommended_decision="Proceed with reduced size",
            invalidation_conditions=["S&P drops 20%"],
        ),
        cio_synthesis="The investment merits approval with position sizing adjustment.",
        final_recommendation="Approve at 3% portfolio weight",
        status=DecisionStatus.APPROVED,
    )


@pytest.fixture
def sample_fiscal_impact() -> FiscalImpact:
    return FiscalImpact(
        jurisdiction="Spain",
        gross_return_pct=12.5,
        tax_rate_effective=23.0,
        net_return_pct=9.625,
        cfc_risk=False,
        withholding_tax_pct=15.0,
    )


@pytest.fixture
def sample_portfolio_asset() -> PortfolioAsset:
    return PortfolioAsset(
        name="Apple Inc.",
        ticker="AAPL",
        asset_class="equities",
        jurisdiction="US",
        quantity=100,
        cost_basis_usd=15_000.0,
        current_value_usd=17_500.0,
        currency="USD",
    )


@pytest.fixture
def sample_message() -> Message:
    return Message(
        type=MessageType.ANALYSIS_REQUEST,
        sender=AgentRole.CIO,
        recipient=AgentRole.FUNDAMENTAL,
        payload={"subject": "AAPL", "urgency": "high"},
        correlation_id="corr-001",
    )


# ---------------------------------------------------------------------------
# Filesystem-backed fixtures (use tmp_path)
# ---------------------------------------------------------------------------

@pytest.fixture
def decision_store(tmp_path) -> DecisionStore:
    return DecisionStore(storage_dir=tmp_path / "decisions")


@pytest.fixture
def memory_manager(tmp_path) -> MemoryManager:
    return MemoryManager(storage_dir=tmp_path / "memory")

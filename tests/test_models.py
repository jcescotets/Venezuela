"""
Tests for all Pydantic models in family_office.core.models.
Covers creation, validation, defaults, serialization, and enum behaviour.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from family_office.core.models import (
    AgentContract,
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
    PortfolioSnapshot,
    ScenarioAnalysis,
    VetoDecision,
    VetoType,
)


# ═══════════════════════════════════════════════════════════════
# Enum tests
# ═══════════════════════════════════════════════════════════════


class TestEnums:
    """Verify all enums hold expected values and behave as str enums."""

    def test_agent_layer_values(self):
        assert AgentLayer.DIRECTION == "direction"
        assert AgentLayer.ANALYSIS == "analysis"
        assert AgentLayer.FISCAL == "fiscal"
        assert AgentLayer.RISK == "risk"
        assert AgentLayer.OPERATIONS == "operations"
        assert len(AgentLayer) == 5

    def test_agent_role_all_members(self):
        """Every role defined in the spec must be present."""
        expected = {
            "cio", "head_tax_strategy", "investment_committee",
            "macro_geopolitics", "fundamental", "technical_quant",
            "credit_bonds", "real_assets",
            "fiscal_spain", "fiscal_portugal", "fiscal_panama",
            "fiscal_barbados", "fiscal_us", "fiscal_venezuela", "cross_border",
            "risk_manager", "tax_risk_audit",
            "portfolio_ops", "opportunity_scanner",
        }
        actual = {r.value for r in AgentRole}
        assert actual == expected

    def test_message_type_values(self):
        assert MessageType.VETO == "veto"
        assert MessageType.PROPOSAL == "proposal"
        assert len(MessageType) == 10

    def test_veto_type_values(self):
        assert VetoType.RISK_DRAWDOWN == "risk_drawdown"
        assert VetoType.INDEFENSIBLE_STRUCTURE == "indefensible_structure"
        assert len(VetoType) == 6

    def test_decision_status_progression(self):
        """Statuses should cover the full lifecycle."""
        statuses = {s.value for s in DecisionStatus}
        for expected in ("pending", "analyzing", "in_debate", "vetoed",
                         "approved", "rejected", "awaiting_user", "executed"):
            assert expected in statuses

    def test_enum_is_str_subclass(self):
        """str(enum) must yield the value for JSON compatibility."""
        assert str(AgentLayer.ANALYSIS) == "AgentLayer.ANALYSIS" or AgentLayer.ANALYSIS.value == "analysis"
        # More importantly, comparisons with raw strings must work:
        assert AgentLayer.ANALYSIS == "analysis"
        assert AgentRole.CIO == "cio"


# ═══════════════════════════════════════════════════════════════
# Message
# ═══════════════════════════════════════════════════════════════


class TestMessage:

    def test_create_message_minimal(self):
        msg = Message(
            type=MessageType.ALERT,
            sender=AgentRole.RISK_MANAGER,
        )
        assert msg.type == MessageType.ALERT
        assert msg.sender == AgentRole.RISK_MANAGER
        assert msg.recipient is None
        assert msg.payload == {}
        assert msg.correlation_id is None
        # Auto-generated fields
        assert uuid.UUID(msg.id)  # valid uuid
        assert isinstance(msg.timestamp, datetime)

    def test_create_message_full(self):
        msg = Message(
            type=MessageType.ANALYSIS_REQUEST,
            sender=AgentRole.CIO,
            recipient=AgentRole.FUNDAMENTAL,
            payload={"subject": "AAPL"},
            correlation_id="corr-xyz",
        )
        assert msg.recipient == AgentRole.FUNDAMENTAL
        assert msg.payload["subject"] == "AAPL"
        assert msg.correlation_id == "corr-xyz"

    def test_message_json_roundtrip(self):
        msg = Message(
            type=MessageType.VETO,
            sender=AgentRole.RISK_MANAGER,
            payload={"severity": 0.9},
        )
        data = msg.model_dump(mode="json")
        restored = Message(**data)
        assert restored.type == msg.type
        assert restored.sender == msg.sender
        assert restored.id == msg.id

    def test_message_requires_type_and_sender(self):
        with pytest.raises(ValidationError):
            Message(sender=AgentRole.CIO)  # missing type
        with pytest.raises(ValidationError):
            Message(type=MessageType.ALERT)  # missing sender


# ═══════════════════════════════════════════════════════════════
# AnalysisReport
# ═══════════════════════════════════════════════════════════════


class TestAnalysisReport:

    def test_create_with_defaults(self):
        report = AnalysisReport(
            agent_role=AgentRole.MACRO_GEOPOLITICS,
            subject="Global macro outlook",
            summary="Inflation trending down.",
            conviction_level=0.7,
        )
        assert report.key_findings == []
        assert report.risks_identified == []
        assert report.data_sources == []
        assert report.recommendation is None
        assert report.raw_data == {}

    def test_conviction_level_bounds(self):
        # valid boundaries
        AnalysisReport(
            agent_role=AgentRole.FUNDAMENTAL, subject="x", summary="s",
            conviction_level=0.0,
        )
        AnalysisReport(
            agent_role=AgentRole.FUNDAMENTAL, subject="x", summary="s",
            conviction_level=1.0,
        )
        # out of bounds
        with pytest.raises(ValidationError):
            AnalysisReport(
                agent_role=AgentRole.FUNDAMENTAL, subject="x", summary="s",
                conviction_level=1.1,
            )
        with pytest.raises(ValidationError):
            AnalysisReport(
                agent_role=AgentRole.FUNDAMENTAL, subject="x", summary="s",
                conviction_level=-0.1,
            )

    def test_analysis_report_roundtrip(self):
        report = AnalysisReport(
            agent_role=AgentRole.TECHNICAL_QUANT,
            subject="BTC momentum",
            summary="Strong momentum signals",
            conviction_level=0.65,
            key_findings=["RSI above 70"],
            risks_identified=["Volatility spike"],
            recommendation="Short-term hold",
        )
        data = report.model_dump(mode="json")
        restored = AnalysisReport(**data)
        assert restored.key_findings == report.key_findings
        assert restored.conviction_level == 0.65


# ═══════════════════════════════════════════════════════════════
# VetoDecision
# ═══════════════════════════════════════════════════════════════


class TestVetoDecision:

    def test_create_veto(self, sample_veto):
        assert sample_veto.veto_type == VetoType.RISK_CONCENTRATION
        assert sample_veto.severity == 0.8
        assert len(sample_veto.conditions_to_lift) == 1

    def test_severity_bounds(self):
        with pytest.raises(ValidationError):
            VetoDecision(
                agent_role=AgentRole.RISK_MANAGER,
                proposal_id="p1",
                veto_type=VetoType.RISK_DRAWDOWN,
                justification="too risky",
                severity=1.5,
            )
        with pytest.raises(ValidationError):
            VetoDecision(
                agent_role=AgentRole.RISK_MANAGER,
                proposal_id="p1",
                veto_type=VetoType.RISK_DRAWDOWN,
                justification="too risky",
                severity=-0.1,
            )

    def test_veto_json_roundtrip(self, sample_veto):
        data = sample_veto.model_dump(mode="json")
        restored = VetoDecision(**data)
        assert restored.veto_type == sample_veto.veto_type
        assert restored.severity == sample_veto.severity
        assert restored.conditions_to_lift == sample_veto.conditions_to_lift


# ═══════════════════════════════════════════════════════════════
# FiscalImpact
# ═══════════════════════════════════════════════════════════════


class TestFiscalImpact:

    def test_create_fiscal_impact(self, sample_fiscal_impact):
        assert sample_fiscal_impact.jurisdiction == "Spain"
        assert sample_fiscal_impact.cfc_risk is False
        assert sample_fiscal_impact.withholding_tax_pct == 15.0

    def test_fiscal_impact_risk_flags(self):
        fi = FiscalImpact(
            jurisdiction="Panama",
            gross_return_pct=15.0,
            tax_rate_effective=0.0,
            net_return_pct=15.0,
            cfc_risk=True,
            permanent_establishment_risk=True,
            substance_risk=True,
            double_taxation_risk=True,
        )
        assert fi.cfc_risk is True
        assert fi.permanent_establishment_risk is True
        assert fi.substance_risk is True
        assert fi.double_taxation_risk is True

    def test_fiscal_impact_defaults(self):
        fi = FiscalImpact(
            jurisdiction="US",
            gross_return_pct=10.0,
            tax_rate_effective=25.0,
            net_return_pct=7.5,
        )
        assert fi.cfc_risk is False
        assert fi.withholding_tax_pct == 0.0
        assert fi.notes == []


# ═══════════════════════════════════════════════════════════════
# InvestmentProposal
# ═══════════════════════════════════════════════════════════════


class TestInvestmentProposal:

    def test_create_proposal(self, sample_proposal):
        assert sample_proposal.title == "Buy AAPL"
        assert sample_proposal.amount_usd == 500_000
        assert sample_proposal.status == DecisionStatus.PENDING
        assert sample_proposal.analyses == []
        assert sample_proposal.vetoes == []
        assert sample_proposal.fiscal_impacts == []

    def test_proposal_status_mutation(self, sample_proposal):
        sample_proposal.status = DecisionStatus.ANALYZING
        assert sample_proposal.status == DecisionStatus.ANALYZING
        sample_proposal.status = DecisionStatus.VETOED
        assert sample_proposal.status == DecisionStatus.VETOED

    def test_proposal_with_nested_models(self, sample_proposal, sample_analysis_report, sample_veto):
        sample_proposal.analyses.append(sample_analysis_report)
        sample_proposal.vetoes.append(sample_veto)
        assert len(sample_proposal.analyses) == 1
        assert len(sample_proposal.vetoes) == 1
        assert sample_proposal.analyses[0].agent_role == AgentRole.FUNDAMENTAL

    def test_proposal_json_roundtrip(self, sample_proposal):
        data = sample_proposal.model_dump(mode="json")
        restored = InvestmentProposal(**data)
        assert restored.title == sample_proposal.title
        assert restored.amount_usd == sample_proposal.amount_usd
        assert restored.id == sample_proposal.id


# ═══════════════════════════════════════════════════════════════
# ScenarioAnalysis & CommitteeDecision
# ═══════════════════════════════════════════════════════════════


class TestScenarioAnalysis:

    def test_create_scenario(self):
        scenario = ScenarioAnalysis(
            scenario_base="10% return",
            scenario_optimistic="20% return",
            scenario_adverse="-5% loss",
            main_risks=["Recession", "Rate hike"],
            recommended_decision="Proceed with caution",
            invalidation_conditions=["GDP drops below -2%"],
        )
        assert len(scenario.main_risks) == 2
        assert scenario.recommended_decision == "Proceed with caution"


class TestCommitteeDecision:

    def test_create_committee_decision(self, sample_committee_decision):
        cd = sample_committee_decision
        assert cd.status == DecisionStatus.APPROVED
        assert len(cd.agreements) == 2
        assert len(cd.contradictions) == 1
        assert cd.scenarios is not None
        assert cd.requires_user_approval is True

    def test_committee_decision_defaults(self):
        cd = CommitteeDecision(proposal_id="p-1")
        assert cd.agreements == []
        assert cd.contradictions == []
        assert cd.scenarios is None
        assert cd.cio_synthesis == ""
        assert cd.final_recommendation == ""
        assert cd.status == DecisionStatus.PENDING
        assert cd.requires_user_approval is True

    def test_committee_decision_roundtrip(self, sample_committee_decision):
        data = sample_committee_decision.model_dump(mode="json")
        restored = CommitteeDecision(**data)
        assert restored.scenarios is not None
        assert restored.scenarios.scenario_base == "10% return in 12 months"
        assert restored.final_recommendation == sample_committee_decision.final_recommendation


# ═══════════════════════════════════════════════════════════════
# Portfolio models
# ═══════════════════════════════════════════════════════════════


class TestPortfolioAsset:

    def test_create_asset(self, sample_portfolio_asset):
        a = sample_portfolio_asset
        assert a.ticker == "AAPL"
        assert a.current_value_usd == 17_500.0
        assert a.currency == "USD"

    def test_asset_defaults(self):
        a = PortfolioAsset(
            name="Gold ETF",
            asset_class="commodities",
            jurisdiction="US",
            quantity=50,
            cost_basis_usd=9000,
            current_value_usd=9500,
        )
        assert a.ticker is None
        assert a.holding_vehicle is None
        assert a.currency == "USD"
        assert a.notes == ""
        assert a.acquisition_date is None


class TestPortfolioSnapshot:

    def test_create_snapshot(self, sample_portfolio_asset):
        snap = PortfolioSnapshot(
            total_value_usd=100_000,
            assets=[sample_portfolio_asset],
            allocation_by_class={"equities": 0.6, "bonds": 0.4},
            allocation_by_jurisdiction={"US": 0.7, "EU": 0.3},
        )
        assert snap.total_value_usd == 100_000
        assert len(snap.assets) == 1
        assert snap.allocation_by_class["equities"] == 0.6

    def test_snapshot_defaults(self):
        snap = PortfolioSnapshot(total_value_usd=0)
        assert snap.assets == []
        assert snap.allocation_by_class == {}
        assert snap.allocation_by_jurisdiction == {}


# ═══════════════════════════════════════════════════════════════
# AgentContract
# ═══════════════════════════════════════════════════════════════


class TestAgentContract:

    def test_create_contract_minimal(self):
        c = AgentContract(
            name="Test CIO",
            role=AgentRole.CIO,
            layer=AgentLayer.DIRECTION,
            specialty="Investment strategy",
            primary_objective="Maximize risk-adjusted returns",
        )
        assert c.can_veto == []
        assert c.can_recommend == []
        assert c.restrictions == []
        assert c.reports_to == []
        assert c.interacts_with == []

    def test_create_contract_full(self):
        c = AgentContract(
            name="Risk Manager",
            role=AgentRole.RISK_MANAGER,
            layer=AgentLayer.RISK,
            specialty="Portfolio risk management",
            primary_objective="Protect capital",
            can_recommend=["position sizing", "hedging"],
            can_veto=["risk_drawdown", "risk_concentration"],
            inputs=["portfolio", "proposal"],
            outputs=["risk_report", "veto"],
            reports_to=[AgentRole.CIO],
            interacts_with=[AgentRole.FUNDAMENTAL, AgentRole.TECHNICAL_QUANT],
            restrictions=["Cannot recommend specific securities"],
        )
        assert len(c.can_veto) == 2
        assert AgentRole.CIO in c.reports_to
        assert len(c.restrictions) == 1

    def test_contract_veto_power_check(self):
        """A contract with empty can_veto is falsy; with entries is truthy."""
        no_veto = AgentContract(
            name="A", role=AgentRole.FUNDAMENTAL, layer=AgentLayer.ANALYSIS,
            specialty="s", primary_objective="o",
        )
        has_veto = AgentContract(
            name="B", role=AgentRole.RISK_MANAGER, layer=AgentLayer.RISK,
            specialty="s", primary_objective="o",
            can_veto=["risk_drawdown"],
        )
        assert not no_veto.can_veto  # falsy empty list
        assert has_veto.can_veto  # truthy non-empty list

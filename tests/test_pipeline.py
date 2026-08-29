"""
Tests for DecisionPipeline, VetoGate, and DebateEngine.
All LLM / agent calls are mocked -- these tests verify orchestration logic,
veto checking, decision validation, and report formatting.
"""

from __future__ import annotations

from datetime import datetime, timezone
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from family_office.core.message_bus import MessageBus
from family_office.core.models import (
    AgentRole,
    AgentLayer,
    AnalysisReport,
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
    ScenarioAnalysis,
    VetoDecision,
    VetoType,
)
from family_office.core.registry import AgentRegistry
from family_office.pipeline.decision_pipeline import DecisionPipeline
from family_office.pipeline.veto_gate import VetoGate, VETO_AUTHORIZED_ROLES
from family_office.pipeline.debate_engine import DebateEngine

from tests.helpers import make_agent, make_pipeline_result


# ═══════════════════════════════════════════════════════════════
# Fixtures
# ═══════════════════════════════════════════════════════════════


@pytest.fixture
def populated_registry(message_bus):
    """Registry with analysis, fiscal, committee, risk and CIO agents (mocked)."""
    registry = AgentRegistry(message_bus)

    # Analysis agents
    for role in [AgentRole.FUNDAMENTAL, AgentRole.MACRO_GEOPOLITICS, AgentRole.TECHNICAL_QUANT]:
        agent = make_agent(name=role.value, role=role, layer=AgentLayer.ANALYSIS)
        agent.analyze = AsyncMock(return_value=AnalysisReport(
            agent_role=role,
            subject="test",
            summary=f"Report from {role.value}",
            conviction_level=0.7,
        ))
        registry.register(agent)

    # Fiscal agents
    for role in [AgentRole.FISCAL_SPAIN, AgentRole.FISCAL_US]:
        agent = make_agent(name=role.value, role=role, layer=AgentLayer.FISCAL)
        agent.analyze = AsyncMock(return_value=AnalysisReport(
            agent_role=role,
            subject="test",
            summary=f"Fiscal report from {role.value}",
            conviction_level=0.6,
        ))
        registry.register(agent)

    # Investment committee
    committee = make_agent("Committee", AgentRole.INVESTMENT_COMMITTEE, AgentLayer.DIRECTION)
    committee.run_debate = AsyncMock(return_value=CommitteeDecision(
        proposal_id="test",
        agreements=["Strong fundamentals"],
        cio_synthesis="Looks good",
        final_recommendation="Approve",
        status=DecisionStatus.APPROVED,
    ))
    registry.register(committee)

    # Risk manager
    risk = make_agent("Risk", AgentRole.RISK_MANAGER, AgentLayer.RISK,
                      can_veto=["risk_drawdown", "risk_concentration"])
    risk.evaluate_proposal = AsyncMock(return_value={"veto_issued": False})
    registry.register(risk)

    # Head of Tax
    tax = make_agent("HeadTax", AgentRole.HEAD_TAX_STRATEGY, AgentLayer.DIRECTION,
                     can_veto=["tax_risk", "regulatory_risk"])
    tax.evaluate_for_veto = AsyncMock(return_value=False)
    registry.register(tax)

    # CIO
    cio = make_agent("CIO", AgentRole.CIO, AgentLayer.DIRECTION)
    cio.synthesize_proposal = AsyncMock(return_value=CommitteeDecision(
        proposal_id="test",
        cio_synthesis="Investment is sound.",
        final_recommendation="Proceed",
        status=DecisionStatus.APPROVED,
    ))
    registry.register(cio)

    return registry


# ═══════════════════════════════════════════════════════════════
# VetoGate -- check_vetoes logic (no LLM needed)
# ═══════════════════════════════════════════════════════════════


class TestVetoGateCheckVetoes:

    def test_no_vetoes_means_not_blocked(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        result = gate.check_vetoes(sample_proposal)
        assert result["blocked"] is False
        assert result["status"] == DecisionStatus.PENDING
        assert result["active_vetoes"] == []
        assert result["can_override"] is True

    def test_high_severity_veto_blocks(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        sample_proposal.vetoes.append(VetoDecision(
            agent_role=AgentRole.RISK_MANAGER,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.RISK_DRAWDOWN,
            justification="Max drawdown exceeded",
            severity=0.9,
        ))
        result = gate.check_vetoes(sample_proposal)
        assert result["blocked"] is True
        assert result["status"] == DecisionStatus.VETOED
        assert len(result["active_vetoes"]) == 1
        assert result["override_warning"] is not None

    def test_low_severity_veto_is_advisory(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        sample_proposal.vetoes.append(VetoDecision(
            agent_role=AgentRole.HEAD_TAX_STRATEGY,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.TAX_RISK,
            justification="Minor tax concern",
            severity=0.3,  # below 0.5 threshold
        ))
        result = gate.check_vetoes(sample_proposal)
        assert result["blocked"] is False
        assert len(result["advisory_vetoes"]) == 1
        assert len(result["active_vetoes"]) == 0

    def test_mixed_severity_vetoes(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        sample_proposal.vetoes.extend([
            VetoDecision(
                agent_role=AgentRole.RISK_MANAGER,
                proposal_id=sample_proposal.id,
                veto_type=VetoType.RISK_CONCENTRATION,
                justification="Concentration",
                severity=0.8,
            ),
            VetoDecision(
                agent_role=AgentRole.HEAD_TAX_STRATEGY,
                proposal_id=sample_proposal.id,
                veto_type=VetoType.TAX_RISK,
                justification="Minor",
                severity=0.2,
            ),
        ])
        result = gate.check_vetoes(sample_proposal)
        assert result["blocked"] is True
        assert len(result["active_vetoes"]) == 1
        assert len(result["advisory_vetoes"]) == 1

    def test_severity_exactly_at_threshold(self, populated_registry, sample_proposal):
        """severity == 0.5 counts as active (>= 0.5)."""
        gate = VetoGate(populated_registry)
        sample_proposal.vetoes.append(VetoDecision(
            agent_role=AgentRole.RISK_MANAGER,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.RISK_DRAWDOWN,
            justification="Borderline",
            severity=0.5,
        ))
        result = gate.check_vetoes(sample_proposal)
        assert result["blocked"] is True


# ═══════════════════════════════════════════════════════════════
# VetoGate -- principal override
# ═══════════════════════════════════════════════════════════════


class TestPrincipalOverride:

    def test_override_changes_status(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        sample_proposal.status = DecisionStatus.VETOED
        gate.principal_override(sample_proposal, "I accept the risk")
        assert sample_proposal.status == DecisionStatus.AWAITING_USER

    def test_veto_history_tracking(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        veto = VetoDecision(
            agent_role=AgentRole.RISK_MANAGER,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.RISK_DRAWDOWN,
            justification="test",
            severity=0.8,
        )
        gate._veto_log.append(veto)
        assert len(gate.veto_history) == 1
        assert gate.veto_history[0].veto_type == VetoType.RISK_DRAWDOWN


# ═══════════════════════════════════════════════════════════════
# VetoGate -- authorized roles mapping
# ═══════════════════════════════════════════════════════════════


class TestVetoAuthorization:

    def test_risk_manager_can_veto_risk_types(self):
        risk_types = VETO_AUTHORIZED_ROLES[AgentRole.RISK_MANAGER]
        assert VetoType.RISK_DRAWDOWN in risk_types
        assert VetoType.RISK_CORRELATION in risk_types
        assert VetoType.RISK_CONCENTRATION in risk_types

    def test_head_tax_can_veto_tax_types(self):
        tax_types = VETO_AUTHORIZED_ROLES[AgentRole.HEAD_TAX_STRATEGY]
        assert VetoType.TAX_RISK in tax_types
        assert VetoType.REGULATORY_RISK in tax_types
        assert VetoType.INDEFENSIBLE_STRUCTURE in tax_types

    def test_only_two_roles_authorized(self):
        assert len(VETO_AUTHORIZED_ROLES) == 2


# ═══════════════════════════════════════════════════════════════
# VetoGate -- evaluate_risk_veto / evaluate_tax_veto
# ═══════════════════════════════════════════════════════════════


class TestVetoEvaluation:

    @pytest.mark.asyncio
    async def test_evaluate_risk_veto_no_veto(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        vetoes = await gate.evaluate_risk_veto(sample_proposal, {})
        assert vetoes == []

    @pytest.mark.asyncio
    async def test_evaluate_risk_veto_when_agent_missing(self, message_bus, sample_proposal):
        empty_registry = AgentRegistry(message_bus)
        gate = VetoGate(empty_registry)
        vetoes = await gate.evaluate_risk_veto(sample_proposal, {})
        assert vetoes == []

    @pytest.mark.asyncio
    async def test_evaluate_tax_veto_no_veto(self, populated_registry, sample_proposal):
        gate = VetoGate(populated_registry)
        vetoes = await gate.evaluate_tax_veto(sample_proposal, "No major issues")
        assert vetoes == []

    @pytest.mark.asyncio
    async def test_evaluate_tax_veto_when_agent_missing(self, message_bus, sample_proposal):
        empty_registry = AgentRegistry(message_bus)
        gate = VetoGate(empty_registry)
        vetoes = await gate.evaluate_tax_veto(sample_proposal, "Analysis")
        assert vetoes == []


# ═══════════════════════════════════════════════════════════════
# DecisionPipeline -- _validate_decision
# ═══════════════════════════════════════════════════════════════


class TestDecisionValidation:

    def test_all_conditions_met(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=3,
            fiscal_count=2,
            committee=sample_committee_decision,
        )
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is True
        assert validation["missing"] == []
        assert all(validation["checks"].values())

    def test_missing_analysis(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=0,
            fiscal_count=2,
            committee=sample_committee_decision,
        )
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is False
        assert "analyzed_by_relevant_agents" in validation["missing"]

    def test_missing_fiscal(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=3,
            fiscal_count=0,
            committee=sample_committee_decision,
        )
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is False
        assert "has_fiscal_impact" in validation["missing"]

    def test_missing_committee(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=3,
            fiscal_count=2,
            committee=None,
        )
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is False
        assert "has_financial_impact" in validation["missing"]
        assert "passed_investment_committee" in validation["missing"]

    def test_missing_risk_evaluation(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=3,
            fiscal_count=2,
            committee=sample_committee_decision,
        )
        # Remove veto_check to simulate missing risk evaluation
        del result["veto_check"]
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is False
        assert "evaluated_by_risk_manager" in validation["missing"]

    def test_empty_result_fails_all_checks(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        result = {"proposal": sample_proposal}
        validation = pipeline._validate_decision(result)
        assert validation["valid"] is False
        assert len(validation["missing"]) == 5


# ═══════════════════════════════════════════════════════════════
# DecisionPipeline -- format_principal_report
# ═══════════════════════════════════════════════════════════════


class TestFormatPrincipalReport:

    def test_report_contains_proposal_details(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        report = pipeline.format_principal_report(result)

        assert "Buy AAPL" in report
        assert "500,000" in report
        assert "equities" in report
        assert "US" in report
        assert "24 meses" in report
        assert "12.5%" in report

    def test_report_shows_awaiting_user_action(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            committee=sample_committee_decision,
            status=DecisionStatus.AWAITING_USER,
        )
        report = pipeline.format_principal_report(result)
        assert "Aprobar" in report or "ACCIÓN REQUERIDA" in report

    def test_report_shows_veto_info(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        veto = VetoDecision(
            agent_role=AgentRole.RISK_MANAGER,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.RISK_CONCENTRATION,
            justification="Portfolio too concentrated",
            severity=0.8,
        )
        result = make_pipeline_result(
            sample_proposal,
            vetoes=[veto],
            status=DecisionStatus.VETOED,
        )
        report = pipeline.format_principal_report(result)
        assert "VETO" in report.upper()
        assert "risk_manager" in report
        assert "Portfolio too concentrated" in report

    def test_report_shows_no_vetoes(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        report = pipeline.format_principal_report(result)
        assert "Sin vetos activos" in report

    def test_report_shows_cio_synthesis(self, populated_registry, sample_proposal, sample_committee_decision):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        report = pipeline.format_principal_report(result)
        # CIO synthesis comes from the committee decision mock
        assert "SÍNTESIS DEL CIO" in report

    def test_report_shows_missing_requirements(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            analysis_count=3,
            fiscal_count=2,
            committee=None,
            status=DecisionStatus.PENDING,
        )
        result["ready_for_principal"] = False
        result["validation"]["missing"] = ["has_financial_impact"]
        report = pipeline.format_principal_report(result)
        assert "REQUISITOS PENDIENTES" in report

    def test_report_vetoed_action(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        result = make_pipeline_result(
            sample_proposal,
            status=DecisionStatus.VETOED,
        )
        report = pipeline.format_principal_report(result)
        assert "override" in report.lower() or "vetos" in report.lower()


# ═══════════════════════════════════════════════════════════════
# DecisionPipeline -- pipeline_log
# ═══════════════════════════════════════════════════════════════


class TestPipelineLog:

    def test_log_starts_empty(self, populated_registry):
        pipeline = DecisionPipeline(populated_registry)
        assert pipeline.get_pipeline_log() == []

    def test_log_records_phases(self, populated_registry):
        pipeline = DecisionPipeline(populated_registry)
        pipeline._log_phase("p1", "TEST_PHASE", "Testing log")
        pipeline._log_phase("p1", "ANOTHER", "Second entry")
        pipeline._log_phase("p2", "OTHER", "Different proposal")

        all_logs = pipeline.get_pipeline_log()
        assert len(all_logs) == 3

        p1_logs = pipeline.get_pipeline_log(proposal_id="p1")
        assert len(p1_logs) == 2
        assert all(e["proposal_id"] == "p1" for e in p1_logs)


# ═══════════════════════════════════════════════════════════════
# DebateEngine -- isolated tests with mocked agents
# ═══════════════════════════════════════════════════════════════


class TestDebateEngine:

    @pytest.mark.asyncio
    async def test_independent_analysis_calls_all_analysis_agents(
        self, populated_registry, sample_proposal
    ):
        engine = DebateEngine(populated_registry)
        reports = await engine.run_independent_analysis(sample_proposal)
        # We registered 3 analysis agents
        assert len(reports) == 3
        roles = {r.agent_role for r in reports}
        assert AgentRole.FUNDAMENTAL in roles
        assert AgentRole.MACRO_GEOPOLITICS in roles

    @pytest.mark.asyncio
    async def test_fiscal_evaluation_calls_fiscal_agents(
        self, populated_registry, sample_proposal
    ):
        engine = DebateEngine(populated_registry)
        reports = await engine.run_fiscal_evaluation(sample_proposal)
        assert len(reports) == 2

    @pytest.mark.asyncio
    async def test_committee_debate_raises_without_committee(
        self, message_bus, sample_proposal
    ):
        """If no committee agent is registered, run_committee_debate raises."""
        empty_registry = AgentRegistry(message_bus)
        engine = DebateEngine(empty_registry)
        with pytest.raises(RuntimeError, match="Investment Committee"):
            await engine.run_committee_debate(sample_proposal, [], [])

    @pytest.mark.asyncio
    async def test_committee_debate_calls_run_debate(
        self, populated_registry, sample_proposal
    ):
        engine = DebateEngine(populated_registry)
        analysis_reports = await engine.run_independent_analysis(sample_proposal)
        fiscal_reports = await engine.run_fiscal_evaluation(sample_proposal)

        decision = await engine.run_committee_debate(
            sample_proposal, analysis_reports, fiscal_reports
        )
        assert isinstance(decision, CommitteeDecision)
        assert decision.status == DecisionStatus.APPROVED

    @pytest.mark.asyncio
    async def test_full_debate_returns_triple(self, populated_registry, sample_proposal):
        engine = DebateEngine(populated_registry)
        analysis, fiscal, committee = await engine.full_debate(sample_proposal)
        assert len(analysis) == 3
        assert len(fiscal) == 2
        assert isinstance(committee, CommitteeDecision)

    @pytest.mark.asyncio
    async def test_analysis_exception_filtered_out(self, populated_registry, sample_proposal):
        """If one agent raises, the others' reports are still collected."""
        engine = DebateEngine(populated_registry)
        # Make one agent fail
        fund_agent = populated_registry.get(AgentRole.FUNDAMENTAL)
        fund_agent.analyze = AsyncMock(side_effect=RuntimeError("LLM timeout"))

        reports = await engine.run_independent_analysis(sample_proposal)
        # 2 of 3 should succeed
        assert len(reports) == 2


# ═══════════════════════════════════════════════════════════════
# Full pipeline integration (mocked agents)
# ═══════════════════════════════════════════════════════════════


class TestFullPipeline:

    @pytest.mark.asyncio
    async def test_process_proposal_happy_path(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        result = await pipeline.process_proposal(sample_proposal)

        assert result["status"] in (DecisionStatus.AWAITING_USER, DecisionStatus.APPROVED)
        assert result["committee_decision"] is not None
        assert result["phases"]["analysis"]["count"] == 3
        assert result["phases"]["fiscal"]["count"] == 2
        assert "validation" in result

    @pytest.mark.asyncio
    async def test_process_proposal_records_log(self, populated_registry, sample_proposal):
        pipeline = DecisionPipeline(populated_registry)
        await pipeline.process_proposal(sample_proposal)

        log = pipeline.get_pipeline_log(proposal_id=sample_proposal.id)
        phases = [e["phase"] for e in log]
        assert "START" in phases
        assert "PIPELINE_COMPLETE" in phases

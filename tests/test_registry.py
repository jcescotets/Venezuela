"""
Tests for AgentRegistry -- agent registration, lookup, and organisational queries.
"""

from __future__ import annotations

import pytest

from family_office.core.message_bus import MessageBus
from family_office.core.models import AgentLayer, AgentRole
from family_office.core.registry import AgentRegistry

from tests.helpers import make_agent


# ═══════════════════════════════════════════════════════════════
# Registration
# ═══════════════════════════════════════════════════════════════


class TestRegistration:

    def test_register_single_agent(self, registry, message_bus):
        agent = make_agent(name="Fund", role=AgentRole.FUNDAMENTAL)
        registry.register(agent)
        assert registry.agent_count == 1

    def test_register_sets_bus(self, registry, message_bus):
        agent = make_agent(name="Fund", role=AgentRole.FUNDAMENTAL)
        assert agent.bus is None  # not yet connected
        registry.register(agent)
        assert agent.bus is message_bus

    def test_register_duplicate_role_raises(self, registry):
        agent1 = make_agent(name="Agent A", role=AgentRole.CIO)
        agent2 = make_agent(name="Agent B", role=AgentRole.CIO)
        registry.register(agent1)
        with pytest.raises(ValueError, match="already registered"):
            registry.register(agent2)

    def test_register_multiple_unique_roles(self, registry):
        roles = [AgentRole.FUNDAMENTAL, AgentRole.MACRO_GEOPOLITICS, AgentRole.TECHNICAL_QUANT]
        for i, role in enumerate(roles):
            registry.register(make_agent(name=f"Agent-{i}", role=role, layer=AgentLayer.ANALYSIS))
        assert registry.agent_count == 3


# ═══════════════════════════════════════════════════════════════
# Lookup
# ═══════════════════════════════════════════════════════════════


class TestLookup:

    def test_get_registered_agent(self, registry):
        agent = make_agent(name="CIO", role=AgentRole.CIO, layer=AgentLayer.DIRECTION)
        registry.register(agent)
        found = registry.get(AgentRole.CIO)
        assert found is agent

    def test_get_unregistered_returns_none(self, registry):
        assert registry.get(AgentRole.OPPORTUNITY_SCANNER) is None

    def test_get_by_layer(self, registry):
        registry.register(make_agent("A1", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))
        registry.register(make_agent("A2", AgentRole.MACRO_GEOPOLITICS, AgentLayer.ANALYSIS))
        registry.register(make_agent("R1", AgentRole.RISK_MANAGER, AgentLayer.RISK))

        analysis = registry.get_by_layer(AgentLayer.ANALYSIS)
        assert len(analysis) == 2
        assert all(a.layer == AgentLayer.ANALYSIS for a in analysis)

        risk = registry.get_by_layer(AgentLayer.RISK)
        assert len(risk) == 1

        operations = registry.get_by_layer(AgentLayer.OPERATIONS)
        assert len(operations) == 0

    def test_get_analysis_agents(self, registry):
        registry.register(make_agent("A1", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))
        registry.register(make_agent("A2", AgentRole.TECHNICAL_QUANT, AgentLayer.ANALYSIS))
        registry.register(make_agent("F1", AgentRole.FISCAL_SPAIN, AgentLayer.FISCAL))

        analysis = registry.get_analysis_agents()
        assert len(analysis) == 2

    def test_get_fiscal_agents(self, registry):
        registry.register(make_agent("F1", AgentRole.FISCAL_SPAIN, AgentLayer.FISCAL))
        registry.register(make_agent("F2", AgentRole.FISCAL_US, AgentLayer.FISCAL))
        registry.register(make_agent("A1", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))

        fiscal = registry.get_fiscal_agents()
        assert len(fiscal) == 2
        assert all(a.layer == AgentLayer.FISCAL for a in fiscal)


# ═══════════════════════════════════════════════════════════════
# Veto power queries
# ═══════════════════════════════════════════════════════════════


class TestVetoPowerQueries:

    def test_get_with_veto_power(self, registry):
        registry.register(make_agent("Risk", AgentRole.RISK_MANAGER, AgentLayer.RISK,
                                     can_veto=["risk_drawdown", "risk_concentration"]))
        registry.register(make_agent("Fund", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))

        veto_agents = registry.get_with_veto_power()
        assert len(veto_agents) == 1
        assert veto_agents[0].role == AgentRole.RISK_MANAGER

    def test_no_agents_with_veto_power(self, registry):
        registry.register(make_agent("Fund", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))
        assert registry.get_with_veto_power() == []


# ═══════════════════════════════════════════════════════════════
# all_agents & agent_count
# ═══════════════════════════════════════════════════════════════


class TestAllAgents:

    def test_all_agents_empty(self, registry):
        assert registry.all_agents() == []
        assert registry.agent_count == 0

    def test_all_agents_returns_list(self, registry):
        registry.register(make_agent("A", AgentRole.CIO, AgentLayer.DIRECTION))
        registry.register(make_agent("B", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))
        all_ = registry.all_agents()
        assert len(all_) == 2
        roles = {a.role for a in all_}
        assert roles == {AgentRole.CIO, AgentRole.FUNDAMENTAL}


# ═══════════════════════════════════════════════════════════════
# Summary
# ═══════════════════════════════════════════════════════════════


class TestSummary:

    def test_summary_contains_agent_info(self, registry):
        registry.register(make_agent("CIO Agent", AgentRole.CIO, AgentLayer.DIRECTION))
        registry.register(make_agent("Risk Mgr", AgentRole.RISK_MANAGER, AgentLayer.RISK,
                                     can_veto=["risk_drawdown"]))

        summary = registry.summary()
        assert "CIO Agent" in summary
        assert "Risk Mgr" in summary
        assert "[VETO]" in summary
        assert "2 agentes activos" in summary

    def test_summary_groups_by_layer(self, registry):
        registry.register(make_agent("A1", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS))
        registry.register(make_agent("A2", AgentRole.MACRO_GEOPOLITICS, AgentLayer.ANALYSIS))
        registry.register(make_agent("R1", AgentRole.RISK_MANAGER, AgentLayer.RISK))

        summary = registry.summary()
        assert "ANALYSIS" in summary
        assert "RISK" in summary

    def test_summary_empty_registry(self, registry):
        summary = registry.summary()
        assert "0 agentes activos" in summary

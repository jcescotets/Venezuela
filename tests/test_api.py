"""
Tests for the FastAPI dashboard API endpoints.
Uses TestClient (sync) and mocks global service dependencies.
"""

from __future__ import annotations

import json
from typing import Any
from unittest.mock import AsyncMock, MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    DecisionStatus,
    InvestmentProposal,
    PortfolioAsset,
    PortfolioSnapshot,
)
from family_office.dashboard.api import app, set_services
from family_office.memory.decision_store import DecisionStore
from family_office.memory.memory_manager import MemoryManager


# ═══════════════════════════════════════════════════════════════
# Helpers
# ═══════════════════════════════════════════════════════════════


def _make_mock_agent(name, role, layer, specialty="Testing", has_veto=False):
    agent = MagicMock()
    agent.name = name
    agent.role = role
    agent.layer = layer
    agent.contract = MagicMock()
    agent.contract.specialty = specialty
    agent.contract.can_veto = ["risk_drawdown"] if has_veto else []
    return agent


def _make_orchestrator(decision_store=None, memory_manager=None):
    """Build a mock orchestrator with a registry containing a few agents."""
    mock_registry = MagicMock()

    agents = [
        _make_mock_agent("CIO", AgentRole.CIO, AgentLayer.DIRECTION, "Investment strategy"),
        _make_mock_agent("Risk Mgr", AgentRole.RISK_MANAGER, AgentLayer.RISK,
                         "Risk management", has_veto=True),
        _make_mock_agent("Fund Analyst", AgentRole.FUNDAMENTAL, AgentLayer.ANALYSIS,
                         "Fundamental analysis"),
    ]

    mock_registry.all_agents.return_value = agents
    mock_registry.agent_count = len(agents)
    mock_registry.summary.return_value = "Test summary"
    mock_registry.get.return_value = None

    orchestrator = MagicMock()
    orchestrator.registry = mock_registry
    return orchestrator


@pytest.fixture
def client(tmp_path):
    """TestClient with all services wired up via mocks."""
    store = DecisionStore(storage_dir=tmp_path / "decisions")
    memory = MemoryManager(storage_dir=tmp_path / "memory")
    orchestrator = _make_orchestrator(store, memory)
    market_svc = MagicMock()
    macro_svc = MagicMock()

    set_services(orchestrator, market_svc, macro_svc, store, memory)
    yield TestClient(app, raise_server_exceptions=False)
    # Clean up global state
    set_services(None, None, None, None, None)


@pytest.fixture
def uninitialized_client():
    """TestClient with services set to None (system not initialized)."""
    set_services(None, None, None, None, None)
    yield TestClient(app, raise_server_exceptions=False)


# ═══════════════════════════════════════════════════════════════
# Organization endpoint
# ═══════════════════════════════════════════════════════════════


class TestOrganizationEndpoint:

    def test_get_organization(self, client):
        resp = client.get("/api/organization")
        assert resp.status_code == 200
        data = resp.json()
        assert "summary" in data
        assert "agent_count" in data
        assert data["agent_count"] == 3
        assert "agents" in data
        assert len(data["agents"]) == 3

    def test_organization_agent_details(self, client):
        resp = client.get("/api/organization")
        data = resp.json()
        roles = {a["role"] for a in data["agents"]}
        assert "cio" in roles
        assert "risk_manager" in roles

        risk_agent = next(a for a in data["agents"] if a["role"] == "risk_manager")
        assert risk_agent["has_veto"] is True

    def test_organization_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/organization")
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Portfolio endpoint
# ═══════════════════════════════════════════════════════════════


class TestPortfolioEndpoint:

    def test_get_portfolio_no_ops_agent(self, client):
        """When no portfolio ops agent is registered, return empty."""
        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["assets"] == []
        assert data["total_value_usd"] == 0

    def test_get_portfolio_with_ops_agent(self, client):
        """When portfolio ops agent exists, return its snapshot."""
        snapshot = PortfolioSnapshot(
            total_value_usd=1_000_000,
            assets=[PortfolioAsset(
                name="AAPL", ticker="AAPL", asset_class="equities",
                jurisdiction="US", quantity=100,
                cost_basis_usd=15_000, current_value_usd=17_500,
            )],
            allocation_by_class={"equities": 1.0},
        )
        # Wire up the mock
        from family_office.dashboard import api as api_module
        mock_ops = MagicMock()
        mock_ops.get_snapshot.return_value = snapshot
        api_module._orchestrator.registry.get.return_value = mock_ops

        resp = client.get("/api/portfolio")
        assert resp.status_code == 200
        data = resp.json()
        assert data["total_value_usd"] == 1_000_000
        assert len(data["assets"]) == 1
        assert data["assets"][0]["ticker"] == "AAPL"

        # Reset
        api_module._orchestrator.registry.get.return_value = None

    def test_portfolio_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/portfolio")
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Decisions endpoints
# ═══════════════════════════════════════════════════════════════


class TestDecisionsEndpoints:

    def test_list_decisions_empty(self, client):
        resp = client.get("/api/decisions")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_list_decisions_with_data(self, client, tmp_path):
        """Store some decisions and list them."""
        from family_office.dashboard import api as api_module
        store = api_module._decision_store

        proposal = InvestmentProposal(
            title="Test Bond",
            asset_class="bonds",
            description="Test",
            amount_usd=200_000,
            expected_gross_return_pct=5.0,
            time_horizon_months=12,
            jurisdiction="EU",
        )
        from tests.helpers import make_pipeline_result
        store.store_decision(proposal, make_pipeline_result(proposal))

        resp = client.get("/api/decisions")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["title"] == "Test Bond"

    def test_list_decisions_filter_status(self, client):
        from family_office.dashboard import api as api_module
        store = api_module._decision_store

        for status in [DecisionStatus.APPROVED, DecisionStatus.VETOED]:
            p = InvestmentProposal(
                title=f"Prop-{status.value}",
                asset_class="equities",
                description="t",
                amount_usd=100_000,
                expected_gross_return_pct=10.0,
                time_horizon_months=12,
                jurisdiction="US",
            )
            p.status = status
            from tests.helpers import make_pipeline_result
            store.store_decision(p, make_pipeline_result(p, status=status))

        resp = client.get("/api/decisions?status=approved")
        assert resp.status_code == 200
        assert len(resp.json()) == 1

    def test_get_decision_by_id(self, client):
        from family_office.dashboard import api as api_module
        store = api_module._decision_store

        proposal = InvestmentProposal(
            title="Specific Decision",
            asset_class="real_estate",
            description="t",
            amount_usd=1_000_000,
            expected_gross_return_pct=8.0,
            time_horizon_months=60,
            jurisdiction="Spain",
        )
        from tests.helpers import make_pipeline_result
        store.store_decision(proposal, make_pipeline_result(proposal))

        resp = client.get(f"/api/decisions/{proposal.id}")
        assert resp.status_code == 200
        data = resp.json()
        assert data["title"] == "Specific Decision"
        assert data["jurisdiction"] == "Spain"

    def test_get_decision_not_found(self, client):
        resp = client.get("/api/decisions/nonexistent-id")
        assert resp.status_code == 404

    def test_decisions_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/decisions")
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Market data endpoints
# ═══════════════════════════════════════════════════════════════


class TestMarketEndpoints:

    def test_stock_endpoint(self, client):
        from family_office.dashboard import api as api_module
        api_module._market_service.get_stock_data = AsyncMock(
            return_value={"ticker": "AAPL", "price": 195.0}
        )

        resp = client.get("/api/market/stock/AAPL")
        assert resp.status_code == 200
        data = resp.json()
        assert data["ticker"] == "AAPL"

    def test_stock_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/market/stock/AAPL")
        assert resp.status_code == 503

    def test_forex_endpoint(self, client):
        from family_office.dashboard import api as api_module
        api_module._market_service.get_forex_rate = AsyncMock(
            return_value={"from": "EUR", "to": "USD", "rate": 1.08}
        )

        resp = client.get("/api/market/forex/eur/usd")
        assert resp.status_code == 200
        data = resp.json()
        assert data["rate"] == 1.08

    def test_forex_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/market/forex/eur/usd")
        assert resp.status_code == 503

    def test_macro_endpoint(self, client):
        from family_office.dashboard import api as api_module
        api_module._macro_service.get_macro_dashboard = AsyncMock(
            return_value={"us": {"gdp": 2.5}, "eu": {"inflation": 3.1}}
        )

        resp = client.get("/api/market/macro")
        assert resp.status_code == 200
        data = resp.json()
        assert "us" in data

    def test_macro_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/market/macro")
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Memory / Criteria / Alerts / Preferences endpoints
# ═══════════════════════════════════════════════════════════════


class TestCriteriaEndpoint:

    def test_get_criteria(self, client):
        resp = client.get("/api/criteria")
        assert resp.status_code == 200
        data = resp.json()
        assert "risk_tolerance" in data
        assert data["risk_tolerance"] == "moderate"

    def test_criteria_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/criteria")
        assert resp.status_code == 503


class TestAlertsEndpoint:

    def test_get_alerts_empty(self, client):
        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        assert resp.json() == []

    def test_get_alerts_with_data(self, client):
        from family_office.dashboard import api as api_module
        mm = api_module._memory_manager
        mm.add_alert("risk", "Test alert", "test_source")

        resp = client.get("/api/alerts")
        assert resp.status_code == 200
        data = resp.json()
        assert len(data) == 1
        assert data[0]["message"] == "Test alert"

    def test_alerts_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/alerts")
        assert resp.status_code == 503


class TestPreferencesEndpoint:

    def test_get_preferences(self, client):
        resp = client.get("/api/preferences")
        assert resp.status_code == 200
        data = resp.json()
        assert data["language"] == "es"
        assert data["communication_style"] == "executive"

    def test_preferences_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.get("/api/preferences")
        assert resp.status_code == 503


# ═══════════════════════════════════════════════════════════════
# Analysis trigger endpoint
# ═══════════════════════════════════════════════════════════════


class TestAnalyzeEndpoint:

    def test_analyze_not_initialized(self, uninitialized_client):
        resp = uninitialized_client.post("/api/analyze", json={
            "title": "Test",
            "asset_class": "equities",
            "description": "Test proposal",
            "amount_usd": 100000,
            "expected_gross_return_pct": 10.0,
        })
        assert resp.status_code == 503

    def test_analyze_validation_error(self, client):
        """Missing required fields should return 422."""
        resp = client.post("/api/analyze", json={
            "title": "Test",
            # missing asset_class, description, amount_usd, expected_gross_return_pct
        })
        assert resp.status_code == 422

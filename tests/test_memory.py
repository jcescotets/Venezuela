"""
Tests for DecisionStore and MemoryManager.
All tests use tmp_path so no real filesystem is polluted.
"""

from __future__ import annotations

import json
from pathlib import Path

import pytest

from family_office.core.models import (
    AgentRole,
    AnalysisReport,
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
    VetoDecision,
    VetoType,
)
from family_office.memory.decision_store import DecisionStore
from family_office.memory.memory_manager import MemoryManager

from tests.helpers import make_pipeline_result


# ═══════════════════════════════════════════════════════════════
# DecisionStore
# ═══════════════════════════════════════════════════════════════


class TestDecisionStoreInit:

    def test_creates_storage_directory(self, tmp_path):
        store_dir = tmp_path / "decisions"
        assert not store_dir.exists()
        store = DecisionStore(storage_dir=store_dir)
        assert store_dir.exists()

    def test_loads_existing_index(self, tmp_path):
        store_dir = tmp_path / "decisions"
        store_dir.mkdir()
        index_data = [{"id": "old-1", "title": "Old Decision", "status": "approved",
                       "amount_usd": 100000, "timestamp": "2024-01-01T00:00:00"}]
        (store_dir / "index.json").write_text(json.dumps(index_data))

        store = DecisionStore(storage_dir=store_dir)
        assert len(store.get_all_decisions()) == 1
        assert store.get_all_decisions()[0]["id"] == "old-1"


class TestDecisionStoreStorageAndRetrieval:

    def test_store_decision(self, decision_store, sample_proposal, sample_committee_decision):
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        decision_id = decision_store.store_decision(sample_proposal, result, sample_committee_decision)

        assert decision_id == sample_proposal.id
        # Index updated
        all_decisions = decision_store.get_all_decisions()
        assert len(all_decisions) == 1
        assert all_decisions[0]["title"] == "Buy AAPL"

    def test_retrieve_decision(self, decision_store, sample_proposal, sample_committee_decision):
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        decision_store.store_decision(sample_proposal, result, sample_committee_decision)

        record = decision_store.get_decision(sample_proposal.id)
        assert record is not None
        assert record["title"] == "Buy AAPL"
        assert record["asset_class"] == "equities"
        assert record["amount_usd"] == 500_000
        assert record["jurisdiction"] == "US"

    def test_retrieve_nonexistent_returns_none(self, decision_store):
        assert decision_store.get_decision("nonexistent-id") is None

    def test_store_multiple_decisions(self, decision_store):
        for i in range(3):
            proposal = InvestmentProposal(
                title=f"Proposal {i}",
                asset_class="equities",
                description=f"Test {i}",
                amount_usd=100_000 * (i + 1),
                expected_gross_return_pct=10.0,
                time_horizon_months=12,
                jurisdiction="US",
            )
            result = make_pipeline_result(proposal)
            decision_store.store_decision(proposal, result)

        all_decisions = decision_store.get_all_decisions()
        assert len(all_decisions) == 3

    def test_filter_by_status(self, decision_store):
        for i, status in enumerate([DecisionStatus.APPROVED, DecisionStatus.VETOED, DecisionStatus.APPROVED]):
            proposal = InvestmentProposal(
                title=f"Proposal {i}",
                asset_class="equities",
                description=f"Test {i}",
                amount_usd=100_000,
                expected_gross_return_pct=10.0,
                time_horizon_months=12,
                jurisdiction="US",
            )
            proposal.status = status
            result = make_pipeline_result(proposal, status=status)
            decision_store.store_decision(proposal, result)

        approved = decision_store.get_all_decisions(status="approved")
        assert len(approved) == 2
        vetoed = decision_store.get_all_decisions(status="vetoed")
        assert len(vetoed) == 1

    def test_decision_records_veto_count(self, decision_store, sample_proposal):
        veto = VetoDecision(
            agent_role=AgentRole.RISK_MANAGER,
            proposal_id=sample_proposal.id,
            veto_type=VetoType.RISK_DRAWDOWN,
            justification="Too risky",
            severity=0.8,
        )
        sample_proposal.vetoes.append(veto)
        result = make_pipeline_result(sample_proposal, vetoes=[veto])
        decision_store.store_decision(sample_proposal, result)

        record = decision_store.get_decision(sample_proposal.id)
        assert record["vetoes_count"] == 1
        assert len(record["vetoes"]) == 1

    def test_decision_includes_committee_data(self, decision_store, sample_proposal, sample_committee_decision):
        result = make_pipeline_result(sample_proposal, committee=sample_committee_decision)
        decision_store.store_decision(sample_proposal, result, sample_committee_decision)

        record = decision_store.get_decision(sample_proposal.id)
        assert "committee" in record
        assert record["committee"]["final_recommendation"] == "Approve at 3% portfolio weight"


class TestDecisionStoreOutcomes:

    def _store_and_get(self, decision_store, proposal, outcome_return=-5.0,
                       lessons=None):
        result = make_pipeline_result(proposal)
        decision_store.store_decision(proposal, result)
        decision_store.store_outcome(
            proposal.id,
            outcome="Lost money",
            actual_return_pct=outcome_return,
            lessons=lessons or ["Don't do it again"],
        )
        return decision_store.get_decision(proposal.id)

    def test_store_outcome(self, decision_store, sample_proposal):
        record = self._store_and_get(decision_store, sample_proposal)
        assert "outcome" in record
        assert record["outcome"]["actual_return_pct"] == -5.0
        assert "Don't do it again" in record["outcome"]["lessons"]

    def test_store_outcome_nonexistent_decision(self, decision_store):
        # Should not raise, just log a warning
        decision_store.store_outcome("ghost-id", "Nothing happened", 0.0)

    def test_outcome_updates_index(self, decision_store, sample_proposal):
        result = make_pipeline_result(sample_proposal)
        decision_store.store_decision(sample_proposal, result)
        decision_store.store_outcome(sample_proposal.id, "Win", actual_return_pct=15.0)

        idx = decision_store.get_all_decisions()
        entry = next(e for e in idx if e["id"] == sample_proposal.id)
        assert entry.get("has_outcome") is True


class TestDecisionStorePatterns:

    def _create_mistake(self, decision_store, asset_class="equities",
                        jurisdiction="US", return_pct=-10.0,
                        lessons=None):
        proposal = InvestmentProposal(
            title=f"Bad {asset_class} in {jurisdiction}",
            asset_class=asset_class,
            description="A mistake",
            amount_usd=100_000,
            expected_gross_return_pct=10.0,
            time_horizon_months=12,
            jurisdiction=jurisdiction,
        )
        result = make_pipeline_result(proposal)
        decision_store.store_decision(proposal, result)
        decision_store.store_outcome(
            proposal.id,
            outcome="Lost money",
            actual_return_pct=return_pct,
            lessons=lessons or ["Lesson learned"],
        )
        return proposal

    def test_get_past_mistakes(self, decision_store):
        self._create_mistake(decision_store, return_pct=-10.0)
        # Positive outcome should not appear
        good = InvestmentProposal(
            title="Winner",
            asset_class="bonds",
            description="Good",
            amount_usd=50_000,
            expected_gross_return_pct=5.0,
            time_horizon_months=6,
            jurisdiction="EU",
        )
        decision_store.store_decision(good, make_pipeline_result(good))
        decision_store.store_outcome(good.id, "Profit", actual_return_pct=8.0)

        mistakes = decision_store.get_past_mistakes()
        assert len(mistakes) == 1
        assert mistakes[0]["actual_return"] == -10.0

    def test_check_repeated_patterns_by_asset_class(self, decision_store):
        self._create_mistake(decision_store, asset_class="equities", jurisdiction="US")
        new_proposal = InvestmentProposal(
            title="Another equity play",
            asset_class="equities",
            description="Same class",
            amount_usd=200_000,
            expected_gross_return_pct=12.0,
            time_horizon_months=12,
            jurisdiction="EU",
        )
        alerts = decision_store.check_repeated_patterns(new_proposal)
        assert len(alerts) >= 1
        assert any("equities" in a for a in alerts)

    def test_check_repeated_patterns_by_jurisdiction(self, decision_store):
        self._create_mistake(decision_store, asset_class="bonds", jurisdiction="Panama",
                             lessons=["Regulatory issues in Panama"])
        new_proposal = InvestmentProposal(
            title="New Panama deal",
            asset_class="real_estate",
            description="Different class, same jurisdiction",
            amount_usd=300_000,
            expected_gross_return_pct=8.0,
            time_horizon_months=36,
            jurisdiction="Panama",
        )
        alerts = decision_store.check_repeated_patterns(new_proposal)
        assert len(alerts) >= 1
        assert any("Panama" in a for a in alerts)

    def test_no_repeated_patterns_when_no_mistakes(self, decision_store, sample_proposal):
        alerts = decision_store.check_repeated_patterns(sample_proposal)
        assert alerts == []

    def test_no_pattern_match_different_class_and_jurisdiction(self, decision_store):
        self._create_mistake(decision_store, asset_class="crypto", jurisdiction="Malta")
        new_proposal = InvestmentProposal(
            title="Safe bonds",
            asset_class="bonds",
            description="Totally different",
            amount_usd=100_000,
            expected_gross_return_pct=5.0,
            time_horizon_months=12,
            jurisdiction="US",
        )
        alerts = decision_store.check_repeated_patterns(new_proposal)
        assert alerts == []


class TestDecisionStoreAssumptions:

    def test_extract_assumptions_from_cio_synthesis(self, decision_store, sample_proposal):
        """If CIO synthesis text contains assumption keywords, they are extracted."""
        committee = CommitteeDecision(
            proposal_id=sample_proposal.id,
            cio_synthesis="Se asume que la inflación permanece bajo 3%.\nEl mercado supone tasas estables.",
            final_recommendation="Approve",
            status=DecisionStatus.APPROVED,
        )
        result = make_pipeline_result(sample_proposal, committee=committee)
        decision_store.store_decision(sample_proposal, result, committee)
        record = decision_store.get_decision(sample_proposal.id)
        # Assumptions should be extracted
        assert len(record["assumptions"]) >= 1


# ═══════════════════════════════════════════════════════════════
# MemoryManager
# ═══════════════════════════════════════════════════════════════


class TestMemoryManagerCriteria:

    def test_default_criteria(self, memory_manager):
        criteria = memory_manager.get_criteria()
        assert criteria["risk_tolerance"] == "moderate"
        assert criteria["target_return_annual_pct"] == 8.0
        assert criteria["max_drawdown_pct"] == 15.0
        assert criteria["liquidity_minimum_pct"] == 20.0
        assert criteria["tax_efficiency_priority"] == "high"
        assert criteria["esg_mandate"] is False
        assert "España" in criteria["preferred_jurisdictions"]

    def test_update_criteria(self, memory_manager):
        memory_manager.update_criteria(
            "risk_tolerance", "aggressive", "Market opportunity"
        )
        criteria = memory_manager.get_criteria()
        assert criteria["risk_tolerance"] == "aggressive"

    def test_criteria_change_log(self, memory_manager):
        memory_manager.update_criteria(
            "max_drawdown_pct", 20.0, "Increased risk appetite"
        )
        criteria = memory_manager.get_criteria()
        change_log = criteria.get("change_log", [])
        assert len(change_log) >= 1
        last = change_log[-1]
        assert last["key"] == "max_drawdown_pct"
        assert last["old_value"] == 15.0  # previous default value
        assert last["new_value"] == 20.0
        assert last["reason"] == "Increased risk appetite"

    def test_criteria_persists(self, memory_manager):
        memory_manager.update_criteria("risk_tolerance", "conservative", "Safety")
        # Re-read from disk
        criteria = memory_manager.get_criteria()
        assert criteria["risk_tolerance"] == "conservative"

    def test_multiple_criteria_updates(self, memory_manager):
        memory_manager.update_criteria("risk_tolerance", "aggressive", "Bull market")
        memory_manager.update_criteria("risk_tolerance", "moderate", "Correction expected")
        criteria = memory_manager.get_criteria()
        assert criteria["risk_tolerance"] == "moderate"
        assert len(criteria["change_log"]) == 2


class TestMemoryManagerAlerts:

    def test_no_alerts_initially(self, memory_manager):
        assert memory_manager.get_alerts() == []

    def test_add_alert(self, memory_manager):
        memory_manager.add_alert("risk", "Correlation spike detected", "risk_manager")
        alerts = memory_manager.get_alerts()
        assert len(alerts) == 1
        assert alerts[0]["type"] == "risk"
        assert alerts[0]["message"] == "Correlation spike detected"
        assert alerts[0]["source"] == "risk_manager"
        assert alerts[0]["resolved"] is False

    def test_add_multiple_alerts(self, memory_manager):
        memory_manager.add_alert("risk", "Alert 1", "risk_manager")
        memory_manager.add_alert("tax", "Alert 2", "head_tax_strategy")
        memory_manager.add_alert("macro", "Alert 3", "macro_geopolitics")
        alerts = memory_manager.get_alerts()
        assert len(alerts) == 3

    def test_resolve_alert(self, memory_manager):
        memory_manager.add_alert("risk", "Spike", "risk_manager")
        memory_manager.add_alert("tax", "CFC issue", "fiscal_spain")
        memory_manager.resolve_alert(0)

        alerts = memory_manager.get_alerts()
        assert alerts[0]["resolved"] is True
        assert "resolved_at" in alerts[0]
        assert alerts[1]["resolved"] is False

    def test_resolve_out_of_range(self, memory_manager):
        memory_manager.add_alert("risk", "Alert", "test")
        # Should not raise
        memory_manager.resolve_alert(99)
        alerts = memory_manager.get_alerts()
        assert alerts[0]["resolved"] is False


class TestMemoryManagerPreferences:

    def test_default_preferences(self, memory_manager):
        prefs = memory_manager.get_preferences()
        assert prefs["communication_style"] == "executive"
        assert prefs["detail_level"] == "high"
        assert prefs["language"] == "es"
        assert prefs["fiscal_residence"] == "España"
        assert prefs["holding_structures"]["portugal_lda"] is True

    def test_update_preference(self, memory_manager):
        memory_manager.update_preference("language", "en")
        prefs = memory_manager.get_preferences()
        assert prefs["language"] == "en"

    def test_add_new_preference(self, memory_manager):
        memory_manager.update_preference("notification_email", "user@example.com")
        prefs = memory_manager.get_preferences()
        assert prefs["notification_email"] == "user@example.com"

    def test_preference_persists(self, memory_manager):
        memory_manager.update_preference("detail_level", "low")
        prefs = memory_manager.get_preferences()
        assert prefs["detail_level"] == "low"


class TestMemoryManagerMacroContext:

    def test_empty_macro_context(self, memory_manager):
        ctx = memory_manager.get_macro_context()
        assert ctx == {}

    def test_update_macro_context(self, memory_manager):
        memory_manager.update_macro_context({
            "us_gdp_growth": 2.5,
            "eu_inflation": 3.1,
        })
        ctx = memory_manager.get_macro_context()
        assert ctx["us_gdp_growth"] == 2.5
        assert ctx["eu_inflation"] == 3.1
        assert "last_updated" in ctx

    def test_macro_context_merges(self, memory_manager):
        memory_manager.update_macro_context({"us_gdp_growth": 2.5})
        memory_manager.update_macro_context({"eu_inflation": 3.1})
        ctx = memory_manager.get_macro_context()
        assert ctx["us_gdp_growth"] == 2.5
        assert ctx["eu_inflation"] == 3.1

    def test_macro_context_overwrites(self, memory_manager):
        memory_manager.update_macro_context({"us_gdp_growth": 2.5})
        memory_manager.update_macro_context({"us_gdp_growth": 1.8})
        ctx = memory_manager.get_macro_context()
        assert ctx["us_gdp_growth"] == 1.8


class TestMemoryManagerFilesystem:

    def test_creates_storage_directory(self, tmp_path):
        mem_dir = tmp_path / "new_memory"
        assert not mem_dir.exists()
        MemoryManager(storage_dir=mem_dir)
        assert mem_dir.exists()

    def test_criteria_written_to_disk(self, memory_manager):
        memory_manager.update_criteria("risk_tolerance", "high", "Test")
        criteria_file = memory_manager._criteria_path
        assert criteria_file.exists()
        data = json.loads(criteria_file.read_text())
        assert data["risk_tolerance"] == "high"

    def test_alerts_written_to_disk(self, memory_manager):
        memory_manager.add_alert("test", "Test alert", "test_source")
        alerts_file = memory_manager._alerts_path
        assert alerts_file.exists()
        data = json.loads(alerts_file.read_text())
        assert len(data) == 1

    def test_preferences_written_to_disk(self, memory_manager):
        memory_manager.update_preference("language", "en")
        prefs_file = memory_manager._preferences_path
        assert prefs_file.exists()
        data = json.loads(prefs_file.read_text())
        assert data["language"] == "en"

    def test_macro_context_written_to_disk(self, memory_manager):
        memory_manager.update_macro_context({"test_key": 42})
        ctx_file = memory_manager._context_path
        assert ctx_file.exists()
        data = json.loads(ctx_file.read_text())
        assert data["test_key"] == 42

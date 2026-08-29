"""
Debate Engine — Implementa la Instrucción 6: Debate Estructurado
=================================================================
Los agentes producen visiones INDEPENDIENTES (no ven los análisis de los demás).
El Investment Committee sintetiza acuerdos, contradicciones y escenarios.
"""

from __future__ import annotations

import asyncio
import logging
from typing import Any

from family_office.core.models import (
    AgentRole,
    AnalysisReport,
    CommitteeDecision,
    InvestmentProposal,
)
from family_office.core.registry import AgentRegistry

logger = logging.getLogger(__name__)


class DebateEngine:
    """
    Orquesta el proceso de debate entre agentes.

    Flujo:
    1. Cada agente de análisis recibe la propuesta de forma AISLADA
    2. Producen análisis independientes (no ven los otros)
    3. Los agentes fiscales evalúan en paralelo
    4. El Investment Committee recibe TODOS los análisis y sintetiza
    5. El debate produce acuerdos, contradicciones y escenarios
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry

    async def run_independent_analysis(
        self,
        proposal: InvestmentProposal,
        context: dict[str, Any] | None = None,
    ) -> list[AnalysisReport]:
        """
        Fase 1: Cada agente analiza INDEPENDIENTEMENTE.
        No comparten resultados entre sí.
        """
        logger.info(f"Starting independent analysis for: {proposal.title}")
        context = context or {}

        # Determine which analysis agents are relevant
        analysis_agents = self.registry.get_analysis_agents()
        tasks = []

        for agent in analysis_agents:
            agent_context = {
                **context,
                "correlation_id": proposal.id,
                "amount_usd": proposal.amount_usd,
                "asset_class": proposal.asset_class,
                "jurisdiction": proposal.jurisdiction,
                "time_horizon_months": proposal.time_horizon_months,
            }
            tasks.append(agent.analyze(proposal.title, agent_context))

        # Run all analyses in parallel — agents don't see each other's work
        reports = await asyncio.gather(*tasks, return_exceptions=True)

        valid_reports = []
        for r in reports:
            if isinstance(r, AnalysisReport):
                valid_reports.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Analysis failed: {r}")

        logger.info(
            f"Independent analysis complete: {len(valid_reports)}/{len(analysis_agents)} reports"
        )
        return valid_reports

    async def run_fiscal_evaluation(
        self,
        proposal: InvestmentProposal,
        context: dict[str, Any] | None = None,
    ) -> list[AnalysisReport]:
        """
        Fase 2: Evaluación fiscal por jurisdicción en paralelo.
        """
        logger.info(f"Starting fiscal evaluation for: {proposal.title}")
        context = context or {}

        fiscal_agents = self.registry.get_fiscal_agents()
        tasks = []

        for agent in fiscal_agents:
            fiscal_context = {
                **context,
                "correlation_id": proposal.id,
                "amount_usd": proposal.amount_usd,
                "asset_class": proposal.asset_class,
                "jurisdiction": proposal.jurisdiction,
                "holding_vehicle": proposal.holding_vehicle,
                "expected_gross_return_pct": proposal.expected_gross_return_pct,
            }
            tasks.append(agent.analyze(proposal.title, fiscal_context))

        reports = await asyncio.gather(*tasks, return_exceptions=True)

        valid_reports = []
        for r in reports:
            if isinstance(r, AnalysisReport):
                valid_reports.append(r)
            elif isinstance(r, Exception):
                logger.error(f"Fiscal analysis failed: {r}")

        logger.info(
            f"Fiscal evaluation complete: {len(valid_reports)}/{len(fiscal_agents)} reports"
        )
        return valid_reports

    async def run_committee_debate(
        self,
        proposal: InvestmentProposal,
        analysis_reports: list[AnalysisReport],
        fiscal_reports: list[AnalysisReport],
    ) -> CommitteeDecision:
        """
        Fase 3: El Investment Committee recibe todos los análisis y debate.
        """
        logger.info(f"Starting committee debate for: {proposal.title}")

        committee = self.registry.get(AgentRole.INVESTMENT_COMMITTEE)
        if committee is None:
            raise RuntimeError("Investment Committee agent not registered")

        all_reports = analysis_reports + fiscal_reports
        decision = await committee.run_debate(proposal, all_reports)

        logger.info(f"Committee debate complete. Status: {decision.status}")
        return decision

    async def full_debate(
        self,
        proposal: InvestmentProposal,
        context: dict[str, Any] | None = None,
    ) -> tuple[list[AnalysisReport], list[AnalysisReport], CommitteeDecision]:
        """
        Ejecuta el debate completo:
        1. Análisis independiente (paralelo)
        2. Evaluación fiscal (paralelo)
        3. Debate del comité (secuencial, con todos los inputs)
        """
        # Phase 1 & 2 run in parallel
        analysis_task = self.run_independent_analysis(proposal, context)
        fiscal_task = self.run_fiscal_evaluation(proposal, context)

        analysis_reports, fiscal_reports = await asyncio.gather(
            analysis_task, fiscal_task
        )

        # Phase 3: Committee debate with all inputs
        committee_decision = await self.run_committee_debate(
            proposal, analysis_reports, fiscal_reports
        )

        return analysis_reports, fiscal_reports, committee_decision

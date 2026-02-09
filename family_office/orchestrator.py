"""
Orchestrator — Motor principal del Family Office Agéntico.
Inicializa todos los agentes, conecta el bus y orquesta operaciones.
"""

from __future__ import annotations

import logging
from typing import Any

from family_office.config.settings import settings
from family_office.core.message_bus import MessageBus
from family_office.core.models import AgentRole, InvestmentProposal
from family_office.core.registry import AgentRegistry

# Agents
from family_office.agents.direction import (
    CIOAgent,
    HeadTaxStrategyAgent,
    InvestmentCommitteeAgent,
)
from family_office.agents.analysis import (
    MacroGeopoliticsAgent,
    FundamentalAgent,
    TechnicalQuantAgent,
    CreditBondsAgent,
    RealAssetsAgent,
)
from family_office.agents.fiscal import (
    FiscalSpainAgent,
    FiscalPortugalAgent,
    FiscalPanamaAgent,
    FiscalBarbadosAgent,
    FiscalUSAgent,
    FiscalVenezuelaAgent,
    CrossBorderAgent,
)
from family_office.agents.risk import RiskManagerAgent, TaxRiskAuditAgent
from family_office.agents.operations import PortfolioOpsAgent, OpportunityScannerAgent

# Pipeline
from family_office.pipeline.decision_pipeline import DecisionPipeline

# Memory
from family_office.memory.decision_store import DecisionStore
from family_office.memory.memory_manager import MemoryManager

# Integrations
from family_office.integrations.market_data import MarketDataService
from family_office.integrations.macro_data import MacroDataService

logger = logging.getLogger(__name__)


class FamilyOfficeOrchestrator:
    """
    Orquestador principal del Family Office.
    Inicializa la organización completa y gestiona el ciclo de vida.
    """

    def __init__(self):
        # Core infrastructure
        self.bus = MessageBus()
        self.registry = AgentRegistry(self.bus)

        # Pipeline
        self.pipeline: DecisionPipeline | None = None

        # Memory
        self.decision_store = DecisionStore()
        self.memory = MemoryManager()

        # Integrations
        self.market_data = MarketDataService()
        self.macro_data = MacroDataService()

        # State
        self._initialized = False

    def initialize(self):
        """Inicializa todos los agentes y los registra en la organización."""
        logger.info("═══ INICIALIZANDO FAMILY OFFICE ═══")

        # ─── Direction Layer ──────────────────────────────────
        self.registry.register(CIOAgent())
        self.registry.register(HeadTaxStrategyAgent())
        self.registry.register(InvestmentCommitteeAgent())

        # ─── Analysis Layer ───────────────────────────────────
        self.registry.register(MacroGeopoliticsAgent())
        self.registry.register(FundamentalAgent())
        self.registry.register(TechnicalQuantAgent())
        self.registry.register(CreditBondsAgent())
        self.registry.register(RealAssetsAgent())

        # ─── Fiscal & Legal Layer ─────────────────────────────
        self.registry.register(FiscalSpainAgent())
        self.registry.register(FiscalPortugalAgent())
        self.registry.register(FiscalPanamaAgent())
        self.registry.register(FiscalBarbadosAgent())
        self.registry.register(FiscalUSAgent())
        self.registry.register(FiscalVenezuelaAgent())
        self.registry.register(CrossBorderAgent())

        # ─── Risk & Control Layer ─────────────────────────────
        self.registry.register(RiskManagerAgent())
        self.registry.register(TaxRiskAuditAgent())

        # ─── Operations Layer ─────────────────────────────────
        self.registry.register(PortfolioOpsAgent())
        self.registry.register(OpportunityScannerAgent())

        # ─── Pipeline ─────────────────────────────────────────
        self.pipeline = DecisionPipeline(self.registry)

        self._initialized = True
        logger.info(self.registry.summary())
        logger.info("═══ FAMILY OFFICE OPERATIVO ═══")

    async def process_proposal(
        self,
        proposal: InvestmentProposal,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Procesa una propuesta de inversión a través del pipeline completo.
        """
        if not self._initialized:
            self.initialize()

        # Check for repeated patterns (Instrucción 9)
        alerts = self.decision_store.check_repeated_patterns(proposal)
        if alerts:
            logger.warning(f"Pattern alerts for {proposal.title}: {alerts}")

        # Get portfolio context
        port_ops = self.registry.get(AgentRole.PORTFOLIO_OPS)
        portfolio = {}
        if port_ops:
            snapshot = port_ops.get_snapshot()
            portfolio = snapshot.model_dump(mode="json")

        # Run pipeline
        result = await self.pipeline.process_proposal(proposal, portfolio, context)

        # Store decision
        committee = result.get("cio_synthesis") or result.get("committee_decision")
        self.decision_store.store_decision(proposal, result, committee)

        # Add pattern alerts to result
        result["pattern_alerts"] = alerts

        return result

    async def quick_analysis(
        self, subject: str, agent_role: AgentRole, context: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Solicita análisis rápido a un agente específico."""
        if not self._initialized:
            self.initialize()

        agent = self.registry.get(agent_role)
        if agent is None:
            return {"error": f"Agent {agent_role.value} not found"}

        report = await agent.analyze(subject, context or {})
        return report.model_dump(mode="json")

    async def scan_opportunities(self, context: dict[str, Any] | None = None) -> dict[str, Any]:
        """Lanza un scan de oportunidades."""
        if not self._initialized:
            self.initialize()

        scanner = self.registry.get(AgentRole.OPPORTUNITY_SCANNER)
        if scanner is None:
            return {"error": "Opportunity Scanner not available"}

        mandate = self.memory.get_criteria()
        scan_context = {
            "mandate": mandate.get("risk_tolerance", "moderate"),
            **(context or {}),
        }

        report = await scanner.analyze("Opportunity Scan", scan_context)
        return report.model_dump(mode="json")

    async def get_macro_briefing(self) -> dict[str, Any]:
        """Obtiene briefing macro del Macro agent + datos de mercado."""
        if not self._initialized:
            self.initialize()

        macro_dashboard = await self.macro_data.get_macro_dashboard()
        macro_agent = self.registry.get(AgentRole.MACRO_GEOPOLITICS)

        briefing = {}
        if macro_agent:
            report = await macro_agent.analyze(
                "Briefing macro diario",
                {"macro_data": macro_dashboard.get("us", {})}
            )
            briefing["analysis"] = report.model_dump(mode="json")

        briefing["market_data"] = macro_dashboard
        return briefing

    def get_organization_summary(self) -> str:
        """Retorna resumen de la organización."""
        if not self._initialized:
            self.initialize()
        return self.registry.summary()

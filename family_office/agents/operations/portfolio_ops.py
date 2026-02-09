"""
Portfolio Operations
=====================
Gestiona el portfolio actual: tracking, rebalanceo, ejecución post-aprobación.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    Message,
    MessageType,
    PortfolioAsset,
    PortfolioSnapshot,
)


def create_portfolio_ops_contract() -> AgentContract:
    return AgentContract(
        name="Portfolio Operations",
        role=AgentRole.PORTFOLIO_OPS,
        layer=AgentLayer.OPERATIONS,
        specialty="Gestión operativa del portfolio, tracking y rebalanceo",
        primary_objective=(
            "Mantener el portfolio actualizado, ejecutar operaciones aprobadas, "
            "monitorear desviaciones respecto a la asignación objetivo, y "
            "proveer datos operativos a todos los agentes del sistema."
        ),
        can_recommend=[
            "Rebalanceo cuando la asignación se desvía >5%",
            "Consolidación de posiciones fragmentadas",
            "Optimización de costes de transacción",
        ],
        can_veto=[],
        inputs=[
            "Portfolio actual con posiciones",
            "Decisiones aprobadas por el Principal",
            "Datos de mercado en tiempo real",
            "Alertas de vencimientos y eventos corporativos",
        ],
        outputs=[
            "Snapshot actualizado del portfolio",
            "Asignación por clase de activo y jurisdicción",
            "Alertas de desviación",
            "Reporting operativo",
        ],
        reports_to=[AgentRole.CIO],
        interacts_with=[
            AgentRole.CIO,
            AgentRole.RISK_MANAGER,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.OPPORTUNITY_SCANNER,
        ],
        restrictions=[
            "NO ejecutar operaciones sin aprobación explícita del Principal",
            "NO modificar posiciones sin registro",
            "NO ignorar costes de transacción en análisis de rebalanceo",
        ],
    )


class PortfolioOpsAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_portfolio_ops_contract(), bus=bus)
        self._portfolio: list[PortfolioAsset] = []

    def _subscribed_message_types(self) -> list[MessageType]:
        return [
            MessageType.DATA_UPDATE,
            MessageType.COMMITTEE_DECISION,
            MessageType.USER_DIRECTIVE,
        ]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        portfolio_value = context.get("total_value", 0)
        assets = context.get("assets", [])
        target_allocation = context.get("target_allocation", {})

        assets_text = ""
        for a in assets:
            if isinstance(a, dict):
                assets_text += (
                    f"  {a.get('name', 'N/A')} | {a.get('asset_class', 'N/A')} | "
                    f"USD {a.get('current_value_usd', 0):,.0f} | "
                    f"{a.get('jurisdiction', 'N/A')}\n"
                )

        target_text = ""
        if target_allocation:
            for cls, pct in target_allocation.items():
                target_text += f"  {cls}: {pct}%\n"

        return (
            f"OPERACIONES DE PORTFOLIO: {subject}\n\n"
            f"VALOR TOTAL: USD {portfolio_value:,.0f}\n\n"
            f"POSICIONES ACTUALES:\n{assets_text or '  Portfolio vacío'}\n\n"
            f"ASIGNACIÓN OBJETIVO:\n{target_text or '  No definida'}\n\n"
            f"ANALIZA:\n"
            f"1. DESVIACIONES — ¿Dónde difiere la asignación actual del objetivo?\n"
            f"2. REBALANCEO — ¿Qué movimientos se necesitan?\n"
            f"3. COSTES — Coste estimado de las operaciones\n"
            f"4. TIMING — ¿Hay urgencia o puede esperar?\n"
            f"5. IMPACTO FISCAL — ¿El rebalanceo genera hechos imponibles?\n"
        )

    def get_snapshot(self) -> PortfolioSnapshot:
        """Genera un snapshot actual del portfolio."""
        total = sum(a.current_value_usd for a in self._portfolio)
        allocation_class: dict[str, float] = {}
        allocation_jurisdiction: dict[str, float] = {}

        for a in self._portfolio:
            pct = (a.current_value_usd / total * 100) if total > 0 else 0
            allocation_class[a.asset_class] = allocation_class.get(a.asset_class, 0) + pct
            allocation_jurisdiction[a.jurisdiction] = (
                allocation_jurisdiction.get(a.jurisdiction, 0) + pct
            )

        return PortfolioSnapshot(
            total_value_usd=total,
            assets=self._portfolio,
            allocation_by_class=allocation_class,
            allocation_by_jurisdiction=allocation_jurisdiction,
        )

    def add_asset(self, asset: PortfolioAsset):
        self._portfolio.append(asset)

    def remove_asset(self, asset_id: str) -> bool:
        for i, a in enumerate(self._portfolio):
            if a.id == asset_id:
                self._portfolio.pop(i)
                return True
        return False

    async def handle_message(self, message: Message):
        self.logger.debug(
            f"Portfolio Ops received: {message.type.value} from {message.sender.value}"
        )

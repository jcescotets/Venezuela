"""
Risk Manager — Con poder de VETO
==================================
Guardián del portfolio. Puede bloquear cualquier decisión que viole
los parámetros de riesgo del Family Office.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    InvestmentProposal,
    Message,
    MessageType,
    VetoType,
)


def create_risk_manager_contract() -> AgentContract:
    return AgentContract(
        name="Risk Manager",
        role=AgentRole.RISK_MANAGER,
        layer=AgentLayer.RISK,
        specialty="Gestión de riesgo de portfolio, drawdown, correlación y concentración",
        primary_objective=(
            "Proteger el patrimonio del Principal evaluando todo riesgo de "
            "inversión: drawdown máximo, correlación entre posiciones, "
            "concentración excesiva, riesgo de liquidez, riesgo de contraparte "
            "y riesgo sistémico. Tiene PODER DE VETO."
        ),
        can_recommend=[
            "Límites de posición y concentración",
            "Coberturas (hedging) necesarias",
            "Reducción de exposición en escenarios de estrés",
            "Niveles de stop-loss a nivel de portfolio",
            "Rebalanceo por riesgo",
        ],
        can_veto=[
            "Drawdown máximo excedido (>15% portfolio)",
            "Correlación excesiva entre posiciones (>0.8 en >30% del portfolio)",
            "Concentración en un solo activo (>20%) o sector (>35%)",
            "Riesgo de liquidez inaceptable (>40% ilíquido)",
            "Riesgo de contraparte no diversificado",
        ],
        inputs=[
            "Portfolio actual con posiciones y valoración",
            "Propuestas de inversión con sizing",
            "Datos de volatilidad y correlación",
            "Análisis de estrés y escenarios",
            "Alertas de mercado y eventos",
        ],
        outputs=[
            "Evaluación de riesgo de cada propuesta",
            "Impacto en métricas de riesgo del portfolio",
            "Alertas de riesgo y vetos",
            "Dashboard de riesgo actualizado",
        ],
        reports_to=[AgentRole.CIO],
        interacts_with=[
            AgentRole.CIO,
            AgentRole.INVESTMENT_COMMITTEE,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.CREDIT_BONDS,
            AgentRole.PORTFOLIO_OPS,
        ],
        restrictions=[
            "NO aprobar operaciones que violen los límites de riesgo",
            "NO flexibilizar límites sin aprobación explícita del Principal",
            "NO ignorar tail risks por baja probabilidad",
            "NO evaluar riesgo sin considerar el portfolio completo",
            "NO sustituir análisis cuantitativo por juicio subjetivo",
        ],
    )


# Risk limits (configurable)
RISK_LIMITS = {
    "max_single_position_pct": 20.0,
    "max_sector_pct": 35.0,
    "max_illiquid_pct": 40.0,
    "max_portfolio_drawdown_pct": 15.0,
    "max_correlation_threshold": 0.8,
    "max_correlated_portfolio_pct": 30.0,
    "max_single_counterparty_pct": 25.0,
}


class RiskManagerAgent(BaseAgent):
    def __init__(self, bus=None, limits: dict | None = None):
        super().__init__(contract=create_risk_manager_contract(), bus=bus)
        self.limits = limits or RISK_LIMITS

    def _subscribed_message_types(self) -> list[MessageType]:
        return [
            MessageType.ANALYSIS_REQUEST,
            MessageType.PROPOSAL,
            MessageType.ANALYSIS_REPORT,
            MessageType.DATA_UPDATE,
        ]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        portfolio = context.get("portfolio", {})
        proposal = context.get("proposal", {})
        market_data = context.get("market_data", {})

        port_text = ""
        if portfolio:
            port_text = f"Valor total: USD {portfolio.get('total_value_usd', 'N/A')}\n"
            allocations = portfolio.get("allocation_by_class", {})
            for cls, pct in allocations.items():
                port_text += f"  {cls}: {pct:.1f}%\n"

        proposal_text = ""
        if proposal:
            proposal_text = (
                f"Activo: {proposal.get('title', 'N/A')}\n"
                f"Monto: USD {proposal.get('amount_usd', 0):,.0f}\n"
                f"Asset class: {proposal.get('asset_class', 'N/A')}\n"
                f"Jurisdicción: {proposal.get('jurisdiction', 'N/A')}\n"
            )

        limits_text = "\n".join(f"  {k}: {v}" for k, v in self.limits.items())

        return (
            f"EVALUACIÓN DE RIESGO: {subject}\n\n"
            f"PORTFOLIO ACTUAL:\n{port_text or '  No disponible'}\n\n"
            f"PROPUESTA:\n{proposal_text or '  Evaluación general'}\n\n"
            f"LÍMITES DE RIESGO:\n{limits_text}\n\n"
            f"EVALÚA:\n"
            f"1. CONCENTRACIÓN — ¿Excede límites por activo, sector, jurisdicción?\n"
            f"2. CORRELACIÓN — ¿Aumenta la correlación del portfolio peligrosamente?\n"
            f"3. DRAWDOWN — ¿Cuál es el drawdown máximo esperado con esta posición?\n"
            f"4. LIQUIDEZ — ¿Qué % del portfolio sería ilíquido?\n"
            f"5. CONTRAPARTE — ¿Hay riesgo de contraparte concentrado?\n"
            f"6. ESTRÉS — ¿Cómo se comporta en escenarios adversos (2008, COVID, tasas +300bp)?\n"
            f"7. VAR/CVAR — Value at Risk y Conditional VaR estimados\n"
            f"8. VETO — ¿Se debe vetar esta operación? SÍ/NO con justificación\n\n"
            f"Si algún límite se viola, emite VETO explícito indicando qué límite y por cuánto."
        )

    async def evaluate_proposal(self, proposal: InvestmentProposal, portfolio: dict) -> dict:
        """Evalúa riesgo de una propuesta contra el portfolio actual."""
        context = {
            "proposal": proposal.model_dump(mode="json"),
            "portfolio": portfolio,
            "correlation_id": proposal.id,
        }

        report = await self.analyze(proposal.title, context)

        # Check for veto conditions
        veto_issued = False
        for risk in report.risks_identified:
            risk_lower = risk.lower()
            if any(kw in risk_lower for kw in ["concentración", "concentration"]):
                await self.issue_veto(
                    proposal.id, VetoType.RISK_CONCENTRATION,
                    risk, severity=0.9
                )
                veto_issued = True
            elif any(kw in risk_lower for kw in ["correlación", "correlation"]):
                await self.issue_veto(
                    proposal.id, VetoType.RISK_CORRELATION,
                    risk, severity=0.8
                )
                veto_issued = True
            elif any(kw in risk_lower for kw in ["drawdown", "caída"]):
                await self.issue_veto(
                    proposal.id, VetoType.RISK_DRAWDOWN,
                    risk, severity=0.9
                )
                veto_issued = True

        return {
            "report": report,
            "veto_issued": veto_issued,
            "limits": self.limits,
        }

    async def handle_message(self, message: Message):
        self.logger.debug(
            f"Risk Manager received: {message.type.value} from {message.sender.value}"
        )

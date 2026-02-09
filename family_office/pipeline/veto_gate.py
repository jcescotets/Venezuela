"""
Veto Gate — Implementa la Instrucción 8: Poder de Veto
=======================================================
Verifica que ningún veto activo bloquea la decisión.
El Risk Manager y el Head of Tax Strategy pueden vetar.
"""

from __future__ import annotations

import logging
from typing import Any

from family_office.core.models import (
    AgentRole,
    DecisionStatus,
    InvestmentProposal,
    VetoDecision,
    VetoType,
)
from family_office.core.registry import AgentRegistry

logger = logging.getLogger(__name__)

# Agents authorized to veto
VETO_AUTHORIZED_ROLES = {
    AgentRole.RISK_MANAGER: [
        VetoType.RISK_DRAWDOWN,
        VetoType.RISK_CORRELATION,
        VetoType.RISK_CONCENTRATION,
    ],
    AgentRole.HEAD_TAX_STRATEGY: [
        VetoType.TAX_RISK,
        VetoType.REGULATORY_RISK,
        VetoType.INDEFENSIBLE_STRUCTURE,
    ],
}


class VetoGate:
    """
    Puerta de veto que toda propuesta debe pasar.

    Reglas:
    - Solo agentes autorizados pueden vetar
    - Cada veto debe ser explícito, justificado y registrado
    - Un veto activo bloquea la propuesta hasta que se resuelve
    - El Principal puede override un veto (con registro)
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self._veto_log: list[VetoDecision] = []

    async def evaluate_risk_veto(
        self, proposal: InvestmentProposal, portfolio: dict[str, Any]
    ) -> list[VetoDecision]:
        """Solicita evaluación de veto al Risk Manager."""
        risk_manager = self.registry.get(AgentRole.RISK_MANAGER)
        if risk_manager is None:
            logger.warning("Risk Manager not available — skipping risk veto check")
            return []

        result = await risk_manager.evaluate_proposal(proposal, portfolio)
        vetoes = []

        if result.get("veto_issued"):
            # Collect vetoes from the bus message log
            from family_office.core.models import MessageType
            bus = self.registry.bus
            messages = bus.get_message_log(
                msg_type=MessageType.VETO,
                sender=AgentRole.RISK_MANAGER,
                correlation_id=proposal.id,
            )
            for msg in messages:
                veto = VetoDecision(**msg.payload)
                vetoes.append(veto)
                self._veto_log.append(veto)

        return vetoes

    async def evaluate_tax_veto(
        self, proposal: InvestmentProposal, fiscal_analysis: str
    ) -> list[VetoDecision]:
        """Solicita evaluación de veto al Head of Tax Strategy."""
        head_tax = self.registry.get(AgentRole.HEAD_TAX_STRATEGY)
        if head_tax is None:
            logger.warning("Head of Tax not available — skipping tax veto check")
            return []

        vetoed = await head_tax.evaluate_for_veto(proposal.id, fiscal_analysis)
        vetoes = []

        if vetoed:
            bus = self.registry.bus
            from family_office.core.models import MessageType
            messages = bus.get_message_log(
                msg_type=MessageType.VETO,
                sender=AgentRole.HEAD_TAX_STRATEGY,
                correlation_id=proposal.id,
            )
            for msg in messages:
                veto = VetoDecision(**msg.payload)
                vetoes.append(veto)
                self._veto_log.append(veto)

        return vetoes

    def check_vetoes(self, proposal: InvestmentProposal) -> dict[str, Any]:
        """
        Verifica el estado de vetos para una propuesta.
        Devuelve un resumen con vetos activos y estado.
        """
        active_vetoes = [v for v in proposal.vetoes if v.severity >= 0.5]
        advisory_vetoes = [v for v in proposal.vetoes if v.severity < 0.5]

        blocked = len(active_vetoes) > 0
        status = DecisionStatus.VETOED if blocked else DecisionStatus.PENDING

        return {
            "blocked": blocked,
            "status": status,
            "active_vetoes": active_vetoes,
            "advisory_vetoes": advisory_vetoes,
            "veto_summary": self._format_veto_summary(active_vetoes),
            "can_override": True,  # Principal siempre puede override
            "override_warning": (
                "ADVERTENCIA: Override de veto queda registrado. "
                "El Principal asume el riesgo identificado."
                if blocked else None
            ),
        }

    def principal_override(self, proposal: InvestmentProposal, reason: str):
        """El Principal override los vetos. Se registra."""
        logger.warning(
            f"PRINCIPAL OVERRIDE on {proposal.id}: {reason} "
            f"({len(proposal.vetoes)} vetoes overridden)"
        )
        proposal.status = DecisionStatus.AWAITING_USER

    def _format_veto_summary(self, vetoes: list[VetoDecision]) -> str:
        if not vetoes:
            return "Sin vetos activos."

        lines = ["VETOS ACTIVOS:"]
        for v in vetoes:
            lines.append(
                f"  ⚠ {v.agent_role.value} — {v.veto_type.value}\n"
                f"    Justificación: {v.justification}\n"
                f"    Severidad: {v.severity:.0%}"
            )
        return "\n".join(lines)

    @property
    def veto_history(self) -> list[VetoDecision]:
        return self._veto_log.copy()

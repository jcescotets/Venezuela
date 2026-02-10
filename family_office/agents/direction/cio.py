"""
CIO — Chief Investment Officer (Agéntico)
==========================================
Agente de máxima jerarquía en la capa de dirección.
Sintetiza análisis de todas las áreas y produce la recomendación final.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    AnalysisReport,
    CommitteeDecision,
    InvestmentProposal,
    Message,
    MessageType,
    ScenarioAnalysis,
)


def create_cio_contract() -> AgentContract:
    return AgentContract(
        name="Chief Investment Officer",
        role=AgentRole.CIO,
        layer=AgentLayer.DIRECTION,
        specialty="Síntesis estratégica y toma de decisiones de inversión",
        primary_objective=(
            "Sintetizar los análisis de todos los agentes especializados en una "
            "recomendación clara, evaluando trade-offs entre retorno, riesgo y "
            "eficiencia fiscal para el beneficiario del Family Office."
        ),
        can_recommend=[
            "Asignación estratégica de activos",
            "Entrada/salida de posiciones",
            "Cambios en la estructura de holding",
            "Priorización de oportunidades de inversión",
            "Rebalanceo de portfolio",
        ],
        can_veto=[],  # El CIO no veta, sintetiza
        inputs=[
            "Reportes de análisis macro/fundamental/técnico/crédito/real assets",
            "Evaluaciones fiscales por jurisdicción",
            "Alertas del Risk Manager",
            "Estado actual del portfolio",
            "Directivas del Principal (usuario)",
        ],
        outputs=[
            "Síntesis de inversión con escenarios",
            "Recomendación final al Principal",
            "Mandatos de ejecución (post-aprobación)",
        ],
        reports_to=[],  # Reporta al Principal (usuario)
        interacts_with=[
            AgentRole.INVESTMENT_COMMITTEE,
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.RISK_MANAGER,
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.FUNDAMENTAL,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.PORTFOLIO_OPS,
        ],
        restrictions=[
            "NO ejecutar decisiones sin aprobación explícita del Principal",
            "NO ignorar vetos activos del Risk Manager o Head of Tax",
            "NO emitir recomendaciones sin análisis fiscal previo",
            "NO simplificar excesivamente: siempre presentar trade-offs",
            "NO ocultar riesgos para favorecer una recomendación",
        ],
    )


class CIOAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_cio_contract(), bus=bus)
        self._pending_analyses: dict[str, list[AnalysisReport]] = {}

    def _subscribed_message_types(self) -> list[MessageType]:
        return [
            MessageType.ANALYSIS_REPORT,
            MessageType.VETO,
            MessageType.COMMITTEE_DECISION,
            MessageType.USER_DIRECTIVE,
        ]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        analyses = context.get("analyses", [])
        vetoes = context.get("vetoes", [])
        fiscal_impacts = context.get("fiscal_impacts", [])
        portfolio_context = context.get("portfolio", "")

        analyses_text = ""
        if analyses:
            for a in analyses:
                if isinstance(a, dict):
                    analyses_text += (
                        f"\n--- {a.get('agent_role', 'unknown')} ---\n"
                        f"Resumen: {a.get('summary', 'N/A')}\n"
                        f"Convicción: {a.get('conviction_level', 'N/A')}\n"
                        f"Hallazgos: {', '.join(a.get('key_findings', []))}\n"
                        f"Riesgos: {', '.join(a.get('risks_identified', []))}\n"
                        f"Recomendación: {a.get('recommendation', 'N/A')}\n"
                    )

        vetoes_text = ""
        if vetoes:
            for v in vetoes:
                if isinstance(v, dict):
                    vetoes_text += (
                        f"\n⚠ VETO de {v.get('agent_role')}: "
                        f"{v.get('justification')} (severidad: {v.get('severity')})\n"
                    )

        fiscal_text = ""
        if fiscal_impacts:
            for f in fiscal_impacts:
                if isinstance(f, dict):
                    fiscal_text += (
                        f"\n--- Jurisdicción: {f.get('jurisdiction')} ---\n"
                        f"Retorno bruto: {f.get('gross_return_pct')}% | "
                        f"Tasa efectiva: {f.get('tax_rate_effective')}% | "
                        f"Retorno neto: {f.get('net_return_pct')}%\n"
                        f"CFC risk: {f.get('cfc_risk')} | "
                        f"EP risk: {f.get('permanent_establishment_risk')}\n"
                    )

        return (
            f"ANÁLISIS DE INVERSIÓN: {subject}\n\n"
            f"CONTEXTO DEL PORTFOLIO:\n{portfolio_context or 'No disponible'}\n\n"
            f"ANÁLISIS RECIBIDOS:{analyses_text or ' Ninguno aún'}\n\n"
            f"VETOS ACTIVOS:{vetoes_text or ' Ninguno'}\n\n"
            f"IMPACTO FISCAL:{fiscal_text or ' Pendiente de evaluación'}\n\n"
            f"INSTRUCCIÓN: Produce una síntesis ejecutiva con:\n"
            f"1. ESCENARIO BASE — el resultado más probable\n"
            f"2. ESCENARIO OPTIMISTA — upside razonable\n"
            f"3. ESCENARIO ADVERSO — downside y tail risks\n"
            f"4. RIESGOS PRINCIPALES — ordenados por impacto\n"
            f"5. DECISIÓN RECOMENDADA — acción concreta\n"
            f"6. CONDICIONES DE INVALIDACIÓN — qué haría cambiar la recomendación\n"
            f"7. RETORNO NETO POST-IMPUESTOS esperado\n\n"
            f"Si hay vetos activos, explica por qué se mantienen o propón cómo resolverlos.\n"
            f"NO presentes la decisión como tomada — el Principal decide."
        )

    async def synthesize_proposal(
        self, proposal: InvestmentProposal
    ) -> CommitteeDecision:
        """Sintetiza todos los análisis de una propuesta en una decisión del comité."""
        context = {
            "analyses": [a.model_dump(mode="json") for a in proposal.analyses],
            "vetoes": [v.model_dump(mode="json") for v in proposal.vetoes],
            "fiscal_impacts": [f.model_dump(mode="json") for f in proposal.fiscal_impacts],
            "correlation_id": proposal.id,
        }

        report = await self.analyze(proposal.title, context)

        decision = CommitteeDecision(
            proposal_id=proposal.id,
            cio_synthesis=report.summary,
            final_recommendation=report.recommendation or "",
            scenarios=ScenarioAnalysis(
                scenario_base="Ver síntesis completa",
                scenario_optimistic="Ver síntesis completa",
                scenario_adverse="Ver síntesis completa",
                main_risks=report.risks_identified,
                recommended_decision=report.recommendation or "Pendiente",
                invalidation_conditions=[],
            ),
        )

        return decision

    async def handle_message(self, message: Message):
        self.logger.debug(f"CIO received: {message.type.value} from {message.sender.value}")

"""
Investment Committee — Agente Colectivo
========================================
Sistema de debate estructurado.
No es un agente individual sino un proceso que:
1. Recoge análisis independientes
2. Identifica acuerdos y contradicciones
3. Genera escenarios
4. Prepara la síntesis para el CIO
"""

from __future__ import annotations

import asyncio
from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    AnalysisReport,
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
    Message,
    MessageType,
    ScenarioAnalysis,
)


def create_committee_contract() -> AgentContract:
    return AgentContract(
        name="Investment Committee",
        role=AgentRole.INVESTMENT_COMMITTEE,
        layer=AgentLayer.DIRECTION,
        specialty="Debate estructurado y síntesis de perspectivas múltiples",
        primary_objective=(
            "Orquestar el proceso de debate entre agentes especializados, "
            "identificar consensos y disensos, generar escenarios y preparar "
            "una síntesis balanceada para el CIO."
        ),
        can_recommend=[
            "Solicitar análisis adicional a agentes específicos",
            "Escalar contradicciones no resueltas al CIO",
            "Pedir clarificación al Principal sobre parámetros",
        ],
        can_veto=[],
        inputs=[
            "Reportes de todos los agentes de análisis",
            "Evaluaciones fiscales consolidadas",
            "Alertas y vetos del Risk Manager y Head of Tax",
        ],
        outputs=[
            "Mapa de acuerdos y contradicciones",
            "Análisis de escenarios (base, optimista, adverso)",
            "Síntesis preparatoria para el CIO",
        ],
        reports_to=[AgentRole.CIO],
        interacts_with=[
            AgentRole.CIO,
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.FUNDAMENTAL,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.CREDIT_BONDS,
            AgentRole.REAL_ASSETS,
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.RISK_MANAGER,
        ],
        restrictions=[
            "NO tomar decisiones — solo preparar la síntesis",
            "NO filtrar ni sesgar opiniones de agentes individuales",
            "NO resolver contradicciones artificialmente — exponerlas",
            "NO omitir ningún veto activo en la síntesis",
        ],
    )


class InvestmentCommitteeAgent(BaseAgent):
    """
    Implementa el debate estructurado (Instrucción 6).
    Los agentes producen visiones independientes → el comité sintetiza.
    """

    def __init__(self, bus=None):
        super().__init__(contract=create_committee_contract(), bus=bus)
        self._debate_rounds: dict[str, list[AnalysisReport]] = {}

    def _subscribed_message_types(self) -> list[MessageType]:
        return [
            MessageType.ANALYSIS_REPORT,
            MessageType.VETO,
            MessageType.PROPOSAL,
        ]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        reports = context.get("independent_reports", [])
        vetoes = context.get("vetoes", [])

        reports_text = ""
        for r in reports:
            if isinstance(r, dict):
                reports_text += (
                    f"\n{'='*40}\n"
                    f"AGENTE: {r.get('agent_role', 'desconocido')}\n"
                    f"CONVICCIÓN: {r.get('conviction_level', 'N/A')}\n"
                    f"RESUMEN: {r.get('summary', 'N/A')}\n"
                    f"HALLAZGOS: {', '.join(r.get('key_findings', []))}\n"
                    f"RIESGOS: {', '.join(r.get('risks_identified', []))}\n"
                    f"RECOMENDACIÓN: {r.get('recommendation', 'N/A')}\n"
                )

        vetoes_text = ""
        for v in vetoes:
            if isinstance(v, dict):
                vetoes_text += (
                    f"\n⚠ VETO — {v.get('agent_role')}: {v.get('justification')} "
                    f"[severidad: {v.get('severity')}]\n"
                )

        return (
            f"DEBATE DEL COMITÉ DE INVERSIÓN: {subject}\n\n"
            f"ANÁLISIS INDEPENDIENTES RECIBIDOS:{reports_text or ' Ninguno'}\n\n"
            f"VETOS ACTIVOS:{vetoes_text or ' Ninguno'}\n\n"
            f"INSTRUCCIONES DE DEBATE:\n"
            f"1. ACUERDOS — ¿En qué coinciden los agentes?\n"
            f"2. CONTRADICCIONES — ¿Dónde hay disenso? No las resuelvas, expónlas.\n"
            f"3. ESCENARIO BASE — resultado más probable según el consenso\n"
            f"4. ESCENARIO OPTIMISTA — best case fundamentado\n"
            f"5. ESCENARIO ADVERSO — worst case y tail risks\n"
            f"6. RIESGOS PRINCIPALES — consolidados y priorizados por impacto\n"
            f"7. SÍNTESIS PARA EL CIO — resumen ejecutivo para toma de decisión\n"
            f"8. CONDICIONES DE INVALIDACIÓN — ¿qué cambiaría la recomendación?\n\n"
            f"IMPORTANTE: Si hay vetos activos, no pueden ser ignorados.\n"
            f"El debate NO produce una decisión — prepara la base para que el CIO decida."
        )

    async def run_debate(
        self,
        proposal: InvestmentProposal,
        independent_reports: list[AnalysisReport],
    ) -> CommitteeDecision:
        """
        Ejecuta un ciclo de debate estructurado.
        Cada reporte se analiza de forma independiente, luego se sintetiza.
        """
        context = {
            "independent_reports": [r.model_dump(mode="json") for r in independent_reports],
            "vetoes": [v.model_dump(mode="json") for v in proposal.vetoes],
            "correlation_id": proposal.id,
        }

        debate_report = await self.analyze(proposal.title, context)

        # Parse the debate into a structured decision
        decision = CommitteeDecision(
            proposal_id=proposal.id,
            agreements=self._extract_section(debate_report.summary, "acuerdo"),
            contradictions=self._extract_section(debate_report.summary, "contradicci"),
            scenarios=ScenarioAnalysis(
                scenario_base=self._extract_named(debate_report.summary, "base"),
                scenario_optimistic=self._extract_named(debate_report.summary, "optimista"),
                scenario_adverse=self._extract_named(debate_report.summary, "adverso"),
                main_risks=debate_report.risks_identified,
                recommended_decision=debate_report.recommendation or "Pendiente de CIO",
                invalidation_conditions=self._extract_section(
                    debate_report.summary, "invalidaci"
                ),
            ),
            status=DecisionStatus.IN_DEBATE,
        )

        # Store for reference
        self._debate_rounds[proposal.id] = independent_reports

        return decision

    def _extract_section(self, text: str, keyword: str) -> list[str]:
        """Extrae items de una sección del texto por keyword."""
        results = []
        in_section = False
        for line in text.split("\n"):
            lower = line.lower()
            if keyword in lower:
                in_section = True
                continue
            if in_section:
                stripped = line.strip()
                if stripped.startswith(("-", "*", "•", "─")):
                    results.append(stripped.lstrip("-*•─ "))
                elif stripped == "" or (stripped[0].isupper() and ":" in stripped):
                    in_section = False
        return results

    def _extract_named(self, text: str, scenario_name: str) -> str:
        """Extrae texto de un escenario nombrado."""
        lines = text.split("\n")
        capture = False
        result = []
        for line in lines:
            if scenario_name.lower() in line.lower():
                capture = True
                # Capture the rest of the line after the keyword
                parts = line.split(":", 1)
                if len(parts) > 1 and parts[1].strip():
                    result.append(parts[1].strip())
                continue
            if capture:
                stripped = line.strip()
                if stripped and not any(
                    kw in stripped.lower()
                    for kw in ["escenario", "riesgo", "decisión", "invalidaci"]
                ):
                    result.append(stripped)
                else:
                    break
        return " ".join(result) if result else f"Ver síntesis completa (escenario {scenario_name})"

    async def handle_message(self, message: Message):
        self.logger.debug(
            f"Committee received: {message.type.value} from {message.sender.value}"
        )

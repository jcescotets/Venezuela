"""
Agente Fiscal — Portugal (Holding LDA)
========================================
Portugal como jurisdicción de holding intermedio.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_portugal_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — Portugal",
        role=AgentRole.FISCAL_PORTUGAL,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad portuguesa: IRC, IRS, SGPS, NHR, holding LDA",
        primary_objective=(
            "Evaluar Portugal como jurisdicción de holding (LDA/SGPS) "
            "y su eficiencia fiscal para el Family Office, considerando "
            "la Participation Exemption, el régimen NHR (si aplicable), "
            "y los CDIs de Portugal."
        ),
        can_recommend=[
            "Estructura de holding LDA/SGPS",
            "Aprovechamiento de Participation Exemption",
            "Flujos óptimos vía Portugal",
            "Planificación con CDIs portugueses",
        ],
        can_veto=[],
        inputs=[
            "Propuestas que involucren entidades portuguesas",
            "Flujos de dividendos/intereses vía Portugal",
            "Estructura societaria con nexo portugués",
        ],
        outputs=[
            "Impacto fiscal en IRC/IRS",
            "Análisis de Participation Exemption",
            "Retenciones en flujos desde/hacia Portugal",
            "Viabilidad de la estructura holding",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.CROSS_BORDER,
        ],
        restrictions=[
            "NO asumir que NHR está vigente sin verificar status actual",
            "NO ignorar substance requirements para holding portuguesa",
            "NO recomendar estructuras que solo sirvan de conduit sin actividad real",
        ],
    )


class FiscalPortugalAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_portugal_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Portugal"

    def get_tax_framework(self) -> str:
        return (
            "PORTUGAL — MARCO FISCAL:\n"
            "• IRC (IS): Tipo general 21% + derramas municipales (hasta ~1.5%)\n"
            "• Participation Exemption: Exención de dividendos y plusvalías de\n"
            "  participaciones ≥10% mantenidas ≥12 meses (sujeto a condiciones)\n"
            "• SGPS: Sociedade Gestora de Participações Sociais — vehículo holding\n"
            "• LDA: Sociedade por Quotas — sociedad limitada portuguesa\n"
            "• NHR: Residente No Habitual — régimen especial (verificar vigencia)\n"
            "  10 años, tipo fijo 20% rentas de alto valor, exención rentas extranjeras\n"
            "• WHT: Dividendos 25% (reducible por CDI), intereses 25%, royalties 25%\n"
            "• CDI España-Portugal: Dividendos 10/15%, intereses 15%, royalties 5%\n"
            "• Directiva Madre-Filial UE: Exención retención dividendos intra-UE\n"
            "• CFC rules: Portugal tiene normas anti-CFC similares a España\n"
            "• Zona Franca de Madeira: Tipo reducido IRC (verificar condiciones)"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        income_type = context.get("income_type", "dividends")
        if income_type == "dividends" and context.get("participation_exemption"):
            return 0.0  # Exención por participación significativa
        return 21.0  # IRC general

    def _assess_substance_risk(self, context: dict[str, Any]) -> bool:
        vehicle = context.get("holding_vehicle", "").lower()
        return "sgps" in vehicle or "lda" in vehicle

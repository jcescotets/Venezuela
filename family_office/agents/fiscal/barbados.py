"""
Agente Fiscal — Barbados
=========================
Barbados como jurisdicción de holding con CDIs y tasas reducidas.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_barbados_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — Barbados",
        role=AgentRole.FISCAL_BARBADOS,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad de Barbados: IBC, SRL, CDIs caribeños",
        primary_objective=(
            "Evaluar Barbados como jurisdicción de holding y operaciones, "
            "con su red de CDIs (incluyendo España vía CARICOM), tipos "
            "impositivos competitivos y marco regulatorio bancario."
        ),
        can_recommend=[
            "Estructuras de IBC o SRL en Barbados",
            "Aprovechamiento de CDIs de Barbados",
            "Operaciones de tesorería regional",
        ],
        can_veto=[],
        inputs=[
            "Propuestas con nexo Barbados",
            "Flujos de dividendos/intereses vía Barbados",
            "Estructuras de holding con Barbados",
        ],
        outputs=[
            "Impacto fiscal en Barbados",
            "Análisis de CDIs aplicables",
            "Riesgo CFC desde España",
            "Substance requirements",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.CROSS_BORDER,
        ],
        restrictions=[
            "NO presentar Barbados como paraíso fiscal — es jurisdicción cooperante",
            "NO ignorar substance requirements locales",
            "NO asumir CDIs sin verificar vigencia y condiciones LOB",
        ],
    )


class FiscalBarbadosAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_barbados_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Barbados"

    def get_tax_framework(self) -> str:
        return (
            "BARBADOS — MARCO FISCAL:\n"
            "• IS: Escala regresiva 5.5% (primeros BBD 1M) a 1% (>BBD 30M)\n"
            "• No hay impuesto sobre plusvalías (capital gains tax)\n"
            "• WHT dividendos: 15% (reducible por CDI)\n"
            "• WHT intereses: 15% (reducible por CDI)\n"
            "• CDI España-Barbados: Verificar existencia y términos\n"
            "• IBC: International Business Company — tasas reducidas\n"
            "• SRL: Society with Restricted Liability\n"
            "• Substance: Barbados exige presencia real (oficina, empleados, directors)\n"
            "• OECD: Barbados es cooperante y cumple estándares de transparencia\n"
            "• CRS: Barbados participa en intercambio automático\n"
            "• FATCA: Signatario\n"
            "• EU listing: No está en lista negra de la UE\n"
            "• CFC España: Posible riesgo por tasas efectivas bajas"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        amount = context.get("amount_usd", 0)
        if amount > 10_000_000:
            return 2.0
        elif amount > 1_000_000:
            return 3.0
        return 5.5

    def _assess_cfc_risk(self, context: dict[str, Any]) -> bool:
        # Tasa baja puede triggear CFC en España
        return True

    def _assess_substance_risk(self, context: dict[str, Any]) -> bool:
        return True  # Siempre relevante en Barbados

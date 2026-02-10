"""
Agente Fiscal — Venezuela
===========================
Venezuela como jurisdicción de origen y contexto patrimonial.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_venezuela_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — Venezuela",
        role=AgentRole.FISCAL_VENEZUELA,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad venezolana: ISLR, control cambiario, riesgo país",
        primary_objective=(
            "Evaluar el impacto fiscal de operaciones con nexo venezolano, "
            "incluyendo ISLR, control de cambios, riesgo de expropiación, "
            "restricciones de repatriación de capitales y el contexto "
            "regulatorio/político actual."
        ),
        can_recommend=[
            "Estrategias de protección de activos venezolanos",
            "Optimización de flujos desde/hacia Venezuela",
            "Vehículos para inversión en activos venezolanos",
            "Planificación ante escenarios de cambio político",
        ],
        can_veto=[],
        inputs=[
            "Propuestas con activos o flujos venezolanos",
            "Situación regulatoria y cambiaria actual",
            "Riesgo político y macroeconómico",
        ],
        outputs=[
            "Impacto ISLR",
            "Análisis de control cambiario",
            "Riesgo país y regulatorio",
            "Estrategias de protección patrimonial",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.CROSS_BORDER,
        ],
        restrictions=[
            "NO asumir estabilidad regulatoria en Venezuela",
            "NO ignorar riesgo de expropiación o intervención estatal",
            "NO recomendar inversiones ilíquidas en Venezuela sin análisis de riesgo país",
            "NO minimizar el impacto del control cambiario",
        ],
    )


class FiscalVenezuelaAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_venezuela_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Venezuela"

    def get_tax_framework(self) -> str:
        return (
            "VENEZUELA — MARCO FISCAL:\n"
            "• ISLR: Tarifas progresivas hasta 34% (personas jurídicas)\n"
            "  Personas naturales: hasta 34% sobre renta mundial (si residente)\n"
            "• Principio de renta mundial para residentes fiscales\n"
            "• IVA: 16% (tasa general)\n"
            "• Impuesto a Grandes Transacciones Financieras: 2-8%\n"
            "• Control cambiario: Restricciones históricas de acceso a divisas\n"
            "  Tipo de cambio oficial vs paralelo (brecha variable)\n"
            "• Retenciones: Dividendos pagados a no residentes — variable\n"
            "• CDI España-Venezuela: NO hay convenio vigente\n"
            "• Riesgo país: ALTO\n"
            "  - Riesgo de expropiación/intervención\n"
            "  - Inestabilidad regulatoria\n"
            "  - Dificultad de repatriación de capitales\n"
            "  - Sanciones internacionales (OFAC) — verificar aplicabilidad\n"
            "• Ley de Precios Justos y controles de precios\n"
            "• Ley Antibloqueo (Ley Constitucional 2020)\n"
            "• Crypto: Venezuela tiene marco para Petro/cripto (ambiguo)"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        return 34.0  # Tasa máxima conservadora

    def _assess_pe_risk(self, context: dict[str, Any]) -> bool:
        return context.get("ve_operations", False)

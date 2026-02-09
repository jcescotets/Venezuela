"""
Agente Fiscal — Estados Unidos
================================
EEUU como jurisdicción de inversión con normativa compleja.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_us_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — United States",
        role=AgentRole.FISCAL_US,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad US: federal tax, FIRPTA, FATCA, withholding, estate tax",
        primary_objective=(
            "Evaluar el impacto fiscal de inversiones en EEUU para un no-residente "
            "(NRA — Non-Resident Alien), incluyendo withholding taxes, FIRPTA en "
            "real estate, estate tax exposure, y compliance FATCA."
        ),
        can_recommend=[
            "Estructuras para invertir en US minimizando WHT",
            "Vehículos para real estate US (LLC, LP, blocker corp)",
            "Optimización de FIRPTA",
            "Planificación de estate tax para NRA",
        ],
        can_veto=[],
        inputs=[
            "Propuestas de inversión en activos US",
            "Flujos de dividendos/intereses de fuente US",
            "Inversiones en real estate US",
            "Exposure a estate tax US",
        ],
        outputs=[
            "WHT aplicable a cada tipo de renta",
            "Impacto FIRPTA en real estate",
            "Estate tax exposure y planificación",
            "Compliance FATCA requirements",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.CROSS_BORDER,
            AgentRole.REAL_ASSETS,
        ],
        restrictions=[
            "NO ignorar estate tax para NRA (aplica a worldwide US situs assets)",
            "NO asumir que LLC es transparente para todos los propósitos fiscales",
            "NO minimizar FIRPTA en operaciones inmobiliarias",
            "NO olvidar que PFIC rules pueden aplicar a fondos non-US",
        ],
    )


class FiscalUSAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_us_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Estados Unidos"

    def get_tax_framework(self) -> str:
        return (
            "ESTADOS UNIDOS — MARCO FISCAL (NRA):\n"
            "• WHT dividendos: 30% (reducible por CDI España-US a 15%)\n"
            "• WHT intereses: 30% (muchas exenciones para portfolio interest)\n"
            "• Capital gains: Generalmente exento para NRA si no hay ECI\n"
            "• FIRPTA: 15% WHT en venta de US Real Property Interest\n"
            "  Plus tributación sobre ganancia real (hasta 37% federal)\n"
            "• Estate tax NRA: 40% sobre US situs assets > USD 60,000\n"
            "  (CDI España-US puede elevar threshold)\n"
            "• ECI (Effectively Connected Income): Tributa como residente\n"
            "• FATCA: Instituciones financieras deben reportar cuentas de US persons\n"
            "• PFIC: Penalización por invertir en fondos non-US (passive foreign IC)\n"
            "• CDI España-US: Vigente, cubre dividendos (15%), intereses (10%),\n"
            "  royalties (5-10%), pensiones, ganancias inmobiliarias\n"
            "• State taxes: Varían significativamente (0-13.3%)\n"
            "• LLC: Transparente o opaca según election — impacto CDI"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        income_type = context.get("income_type", "dividends")
        has_treaty = context.get("treaty_benefits", True)
        if income_type == "dividends":
            return 15.0 if has_treaty else 30.0
        elif income_type == "interest":
            return 0.0 if context.get("portfolio_interest") else (10.0 if has_treaty else 30.0)
        elif income_type == "capital_gains":
            return 0.0  # NRA generally exempt
        elif income_type == "real_estate":
            return 20.0  # FIRPTA effective
        return 21.0  # Corporate rate

    def _assess_pe_risk(self, context: dict[str, Any]) -> bool:
        # PE risk if there's a US office or dependent agent
        return context.get("us_office", False) or context.get("us_agent", False)

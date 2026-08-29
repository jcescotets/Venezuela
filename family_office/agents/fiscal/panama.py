"""
Agente Fiscal — Panamá (Ley 52)
=================================
Panamá como jurisdicción de protección patrimonial y operaciones.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_panama_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — Panamá",
        role=AgentRole.FISCAL_PANAMA,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad panameña: territorialidad, Ley 52, fundaciones, SEM",
        primary_objective=(
            "Evaluar Panamá como jurisdicción bajo su principio de territorialidad "
            "(solo grava rentas de fuente panameña), las ventajas de la Ley 52 "
            "(SEM — Sedes de Empresas Multinacionales), fundaciones de interés "
            "privado y su interacción con el régimen CFC español."
        ),
        can_recommend=[
            "Estructura SEM bajo Ley 52",
            "Fundación de interés privado para protección patrimonial",
            "Optimización de operaciones regionales desde Panamá",
            "Cuentas y custodia en jurisdicción panameña",
        ],
        can_veto=[],
        inputs=[
            "Propuestas con nexo panameño",
            "Estructuras de holding con componente Panamá",
            "Operaciones de protección patrimonial",
        ],
        outputs=[
            "Impacto fiscal en Panamá",
            "Análisis de territorialidad",
            "Riesgo CFC visto desde España",
            "Viabilidad de estructura panameña",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.CROSS_BORDER,
        ],
        restrictions=[
            "NO asumir que Panamá es 0% fiscal automáticamente",
            "NO ignorar que rentas de fuente panameña SÍ tributan",
            "NO olvidar la lista gris/negra de la UE y su impacto en CDIs",
            "NO recomendar fundaciones opacas — CRS aplica",
        ],
    )


class FiscalPanamaAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_panama_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Panamá"

    def get_tax_framework(self) -> str:
        return (
            "PANAMÁ — MARCO FISCAL:\n"
            "• Principio de TERRITORIALIDAD: Solo grava rentas de fuente panameña\n"
            "• IS: 25% sobre rentas de fuente panameña\n"
            "• Dividendos: 10% WHT (5% si provienen de rentas extranjeras)\n"
            "• Ley 52 (SEM): Régimen para sedes de multinacionales\n"
            "  - Exención de IS sobre rentas de fuente extranjera\n"
            "  - Visas especiales para personal\n"
            "  - Requisitos de substance y empleo local\n"
            "• Fundación de Interés Privado (Ley 25 de 1995):\n"
            "  - Vehículo de protección patrimonial\n"
            "  - NO es fiscalmente transparente per se\n"
            "  - CRS: reporta a jurisdicción de residencia del beneficiario\n"
            "• NO tiene CDI con España (importante para retenciones)\n"
            "• Lista de la UE: Panamá ha estado en lista gris\n"
            "• FATCA: Panamá es signatario (IGA Modelo 1)\n"
            "• CFC España: Alta probabilidad de imputación CFC\n"
            "  por tributación efectiva < 75% del IS español"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        source = context.get("income_source", "foreign")
        if source == "foreign":
            return 0.0  # Territorialidad — rentas extranjeras exentas
        return 25.0  # Rentas de fuente panameña

    def _assess_cfc_risk(self, context: dict[str, Any]) -> bool:
        # Panamá siempre tiene riesgo CFC alto visto desde España
        return True

    def _assess_substance_risk(self, context: dict[str, Any]) -> bool:
        vehicle = context.get("holding_vehicle", "").lower()
        return "fundacion" in vehicle or "sem" in vehicle

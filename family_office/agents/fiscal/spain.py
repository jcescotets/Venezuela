"""
Agente Fiscal — España (Residencia del Principal)
===================================================
Jurisdicción crítica: toda renta mundial se declara aquí.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_spain_contract() -> AgentContract:
    return AgentContract(
        name="Fiscal Advisor — Spain",
        role=AgentRole.FISCAL_SPAIN,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad española: IRPF, IS, IP, IRNR, normativa CFC",
        primary_objective=(
            "Evaluar el impacto fiscal en España como país de residencia del "
            "Principal. España grava la renta mundial — toda decisión de inversión "
            "debe analizarse bajo el prisma del IRPF/IS español, incluyendo "
            "régimen CFC (Art. 100 LIS), transparencia fiscal internacional, "
            "y obligación de declarar bienes en el exterior (Modelo 720)."
        ),
        can_recommend=[
            "Optimización de base imponible en IRPF",
            "Estructuras societarias españolas (ETVE, holding)",
            "Timing de realizaciones de plusvalías",
            "Aplicación de exenciones y deducciones",
        ],
        can_veto=[],  # El veto fiscal lo ejerce Head of Tax
        inputs=[
            "Propuestas de inversión con jurisdicción y vehículo",
            "Rentas obtenidas en el exterior",
            "Estructura societaria actual",
            "Cambios normativos AEAT/DGT",
        ],
        outputs=[
            "Impacto en IRPF/IS del Principal",
            "Riesgo CFC por jurisdicción de origen",
            "Obligaciones formales (720, DAC6)",
            "Retorno neto post-impuestos desde perspectiva española",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.CROSS_BORDER,
            AgentRole.TAX_RISK_AUDIT,
            AgentRole.FISCAL_PORTUGAL,
            AgentRole.FISCAL_PANAMA,
        ],
        restrictions=[
            "NO asumir que el régimen Beckham aplica sin verificar elegibilidad",
            "NO ignorar la obligación de reportar bienes en el exterior (720)",
            "NO minimizar riesgo de inspección de AEAT en rentas extranjeras",
            "NO asumir que CDIs eliminan toda tributación en España",
        ],
    )


class FiscalSpainAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_spain_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "España"

    def get_tax_framework(self) -> str:
        return (
            "ESPAÑA — MARCO FISCAL:\n"
            "• IRPF: Rentas del ahorro 19-28% (dividendos, intereses, plusvalías)\n"
            "• IS: Tipo general 25%, ETVE exención dividendos y plusvalías participación ≥5%\n"
            "• IP: Impuesto sobre Patrimonio (varía por CCAA, 0.2-3.5%)\n"
            "• ITSGF: Impuesto Temporal de Solidaridad Grandes Fortunas\n"
            "• CFC: Art. 100 LIS — imputación de rentas de entidades no residentes\n"
            "  controladas si tributación efectiva < 75% del IS español\n"
            "• Modelo 720: Declaración informativa de bienes en el exterior >50.000€\n"
            "• DAC6: Reporte de planificaciones fiscales transfronterizas\n"
            "• CDIs: España tiene ~90 convenios de doble imposición\n"
            "• AEAT: Hacienda tiene acceso a CRS (intercambio automático)\n"
            "• Régimen de transparencia fiscal internacional\n"
            "• Exit tax en caso de traslado de residencia"
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        income_type = context.get("income_type", "capital_gains")
        amount = context.get("amount_usd", 0)
        # Escala progresiva rentas del ahorro 2024+
        if income_type in ("dividends", "interest", "capital_gains"):
            if amount <= 6000:
                return 19.0
            elif amount <= 50000:
                return 21.0
            elif amount <= 200000:
                return 23.0
            elif amount <= 300000:
                return 27.0
            else:
                return 28.0
        return 25.0  # Tipo IS general

    def _assess_cfc_risk(self, context: dict[str, Any]) -> bool:
        # CFC risk if controlled entity in low-tax jurisdiction
        source = context.get("source_jurisdiction", "").lower()
        low_tax = ["panama", "barbados", "dubai", "bahamas", "cayman", "bvi"]
        return any(j in source for j in low_tax)

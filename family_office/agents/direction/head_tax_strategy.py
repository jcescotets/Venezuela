"""
Head of Tax Strategy
=====================
Máxima autoridad fiscal del Family Office.
Tiene PODER DE VETO por riesgo fiscal, regulatorio o estructura indefendible.
Coordina los agentes fiscales por jurisdicción.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    Message,
    MessageType,
    VetoType,
)


def create_head_tax_contract() -> AgentContract:
    return AgentContract(
        name="Head of Tax Strategy",
        role=AgentRole.HEAD_TAX_STRATEGY,
        layer=AgentLayer.DIRECTION,
        specialty="Estrategia fiscal internacional y planificación patrimonial",
        primary_objective=(
            "Garantizar que toda decisión de inversión sea fiscalmente eficiente, "
            "legalmente defendible y cumpla con las obligaciones tributarias en "
            "todas las jurisdicciones relevantes (España como residencia fiscal, "
            "Portugal, Panamá, Barbados, EEUU, Venezuela)."
        ),
        can_recommend=[
            "Estructuras de holding óptimas por jurisdicción",
            "Vehículos de inversión fiscalmente eficientes",
            "Timing de operaciones por ventanas fiscales",
            "Reorganizaciones societarias",
            "Aplicación de convenios de doble imposición",
        ],
        can_veto=[
            "Riesgo fiscal inaceptable (CFC, EP, substance)",
            "Riesgo regulatorio (FATCA, CRS, DAC6)",
            "Estructura fiscalmente indefendible ante inspección",
        ],
        inputs=[
            "Propuestas de inversión con jurisdicción y vehículo",
            "Análisis de los agentes fiscales por país",
            "Cambios regulatorios y normativos",
            "Consultas sobre reestructuración",
        ],
        outputs=[
            "Evaluación fiscal consolidada multi-jurisdicción",
            "Retorno neto post-impuestos estimado",
            "Alertas y vetos fiscales",
            "Mapa de flujos inter-sociedades con retenciones",
        ],
        reports_to=[AgentRole.CIO],
        interacts_with=[
            AgentRole.CIO,
            AgentRole.INVESTMENT_COMMITTEE,
            AgentRole.FISCAL_SPAIN,
            AgentRole.FISCAL_PORTUGAL,
            AgentRole.FISCAL_PANAMA,
            AgentRole.FISCAL_BARBADOS,
            AgentRole.FISCAL_US,
            AgentRole.FISCAL_VENEZUELA,
            AgentRole.CROSS_BORDER,
            AgentRole.TAX_RISK_AUDIT,
        ],
        restrictions=[
            "NO aprobar estructuras que no tengan sustancia económica real",
            "NO ignorar normativa CFC de España (Arts. 100 LIS)",
            "NO asumir que un CDI aplica sin verificar condiciones",
            "NO recomendar estructuras que dependan de opacidad fiscal",
            "NO minimizar riesgos regulatorios para favorecer retorno",
        ],
    )


class HeadTaxStrategyAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_head_tax_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [
            MessageType.ANALYSIS_REQUEST,
            MessageType.ANALYSIS_REPORT,
            MessageType.PROPOSAL,
        ]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        jurisdiction = context.get("jurisdiction", "multi-jurisdicción")
        amount = context.get("amount_usd", "no especificado")
        vehicle = context.get("holding_vehicle", "no definido")
        asset_class = context.get("asset_class", "no especificado")
        fiscal_reports = context.get("fiscal_reports", [])

        fiscal_text = ""
        for fr in fiscal_reports:
            if isinstance(fr, dict):
                fiscal_text += (
                    f"\n--- {fr.get('jurisdiction', 'N/A')} ---\n"
                    f"{fr.get('summary', 'Sin detalle')}\n"
                )

        return (
            f"EVALUACIÓN FISCAL: {subject}\n\n"
            f"Jurisdicción principal: {jurisdiction}\n"
            f"Monto: USD {amount}\n"
            f"Vehículo: {vehicle}\n"
            f"Clase de activo: {asset_class}\n\n"
            f"ANÁLISIS FISCALES POR JURISDICCIÓN:{fiscal_text or ' Pendientes'}\n\n"
            f"RESIDENCIA FISCAL DEL PRINCIPAL: España\n\n"
            f"Evalúa:\n"
            f"1. IMPACTO FISCAL DESDE ESPAÑA — como país de residencia\n"
            f"2. RIESGO CFC — ¿la renta podría ser imputada al residente español?\n"
            f"3. ESTABLECIMIENTO PERMANENTE — ¿hay riesgo de EP en alguna jurisdicción?\n"
            f"4. SUBSTANCE — ¿las entidades intermedias tienen sustancia real?\n"
            f"5. DOBLE IMPOSICIÓN — ¿hay CDI aplicable? ¿Se cumplen condiciones?\n"
            f"6. RETENCIONES — en toda la cadena de flujos (dividendos, intereses, royalties)\n"
            f"7. RETORNO NETO — después de TODOS los impuestos en TODAS las jurisdicciones\n"
            f"8. DEFENDIBILIDAD — ¿esta estructura aguanta una inspección de la AEAT?\n\n"
            f"Si el riesgo fiscal es inaceptable, indica VETO con justificación.\n"
            f"No uses tecnicismos sin explicar su impacto práctico."
        )

    async def evaluate_for_veto(
        self, proposal_id: str, fiscal_analysis: str
    ) -> bool:
        """Evalúa si una propuesta merece veto fiscal."""
        prompt = (
            f"Basándote en este análisis fiscal, ¿debería emitir VETO?\n\n"
            f"{fiscal_analysis}\n\n"
            f"Responde SOLO: VETO o NO_VETO, seguido de justificación en una línea."
        )
        from family_office.core.llm_client import call_llm

        response = await call_llm(
            system_prompt=self.build_system_prompt(),
            user_prompt=prompt,
        )

        if response.strip().upper().startswith("VETO"):
            justification = response.split("\n")[0].replace("VETO", "").strip(" :-")
            await self.issue_veto(
                proposal_id=proposal_id,
                veto_type=VetoType.TAX_RISK,
                justification=justification or "Riesgo fiscal inaceptable",
                severity=0.9,
            )
            return True
        return False

    async def handle_message(self, message: Message):
        self.logger.debug(
            f"Head Tax received: {message.type.value} from {message.sender.value}"
        )

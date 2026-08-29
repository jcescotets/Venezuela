"""
Opportunity Scanner
====================
Escanea mercados y fuentes de datos en busca de oportunidades de inversión.
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
)


def create_scanner_contract() -> AgentContract:
    return AgentContract(
        name="Opportunity Scanner",
        role=AgentRole.OPPORTUNITY_SCANNER,
        layer=AgentLayer.OPERATIONS,
        specialty="Screening y detección de oportunidades de inversión",
        primary_objective=(
            "Escanear continuamente mercados, noticias y fuentes de datos para "
            "identificar oportunidades de inversión que coincidan con el mandato "
            "del Family Office: activos infravalorados, eventos corporativos, "
            "dislocaciones de mercado, y oportunidades fiscalmente eficientes."
        ),
        can_recommend=[
            "Oportunidades de inversión para análisis",
            "Alertas de eventos de mercado relevantes",
            "Screening por criterios predefinidos",
        ],
        can_veto=[],
        inputs=[
            "Datos de mercado (precios, volúmenes, flujos)",
            "Noticias financieras y eventos corporativos",
            "Screeners (value, momentum, quality, yield)",
            "Mandato de inversión del Family Office",
        ],
        outputs=[
            "Lista de oportunidades detectadas",
            "Alertas de mercado relevantes",
            "Pre-screening de ideas de inversión",
        ],
        reports_to=[AgentRole.CIO, AgentRole.PORTFOLIO_OPS],
        interacts_with=[
            AgentRole.CIO,
            AgentRole.FUNDAMENTAL,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.MACRO_GEOPOLITICS,
        ],
        restrictions=[
            "NO generar señales de compra/venta — solo screening",
            "NO filtrar oportunidades por sesgo propio",
            "NO ignorar clases de activos fuera del foco habitual",
        ],
    )


class OpportunityScannerAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_scanner_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.DATA_UPDATE, MessageType.USER_DIRECTIVE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        mandate = context.get("mandate", "Preservación de capital con crecimiento moderado")
        asset_classes = context.get("asset_classes", [
            "Renta variable global", "Renta fija", "Real assets", "Alternativos"
        ])
        screens = context.get("screens", [])
        market_data = context.get("market_data", {})
        excluded = context.get("excluded_sectors", [])

        screens_text = ""
        for s in screens:
            if isinstance(s, dict):
                screens_text += f"  {s.get('name', 'N/A')}: {s.get('criteria', 'N/A')}\n"

        return (
            f"OPORTUNITY SCAN: {subject}\n\n"
            f"MANDATO: {mandate}\n"
            f"CLASES DE ACTIVO: {', '.join(asset_classes)}\n"
            f"EXCLUIDOS: {', '.join(excluded) if excluded else 'Ninguno'}\n\n"
            f"SCREENS ACTIVOS:\n{screens_text or '  Aplicar criterios estándar de value + quality'}\n\n"
            f"DETECTA:\n"
            f"1. VALUE — Activos cotizando por debajo de valor intrínseco estimado\n"
            f"2. MOMENTUM — Activos con momentum positivo y fundamentos sólidos\n"
            f"3. YIELD — Oportunidades de renta (dividendos, cupones, rentas)\n"
            f"4. EVENT — Eventos corporativos (M&A, spin-offs, restructuraciones)\n"
            f"5. DISLOCATION — Dislocaciones de mercado o ineficiencias\n"
            f"6. MACRO — Oportunidades por cambio de ciclo o política monetaria\n\n"
            f"Para cada oportunidad indica:\n"
            f"- Activo / sector / mercado\n"
            f"- Tesis resumida (1-2 líneas)\n"
            f"- Urgencia (alta/media/baja)\n"
            f"- Próximo paso recomendado\n"
        )

    async def handle_message(self, message: Message):
        self.logger.debug(
            f"Scanner received: {message.type.value} from {message.sender.value}"
        )

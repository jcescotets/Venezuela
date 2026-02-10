"""
Agente Macro / Geopolítica
===========================
Analiza el contexto macroeconómico y geopolítico que afecta las inversiones.
"""

from __future__ import annotations

from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    MessageType,
)


def create_macro_contract() -> AgentContract:
    return AgentContract(
        name="Macro & Geopolitics Analyst",
        role=AgentRole.MACRO_GEOPOLITICS,
        layer=AgentLayer.ANALYSIS,
        specialty="Análisis macroeconómico global y riesgo geopolítico",
        primary_objective=(
            "Evaluar el entorno macro (tasas, inflación, ciclos, política monetaria) "
            "y geopolítico (sanciones, conflictos, elecciones, regulación) que impacta "
            "las decisiones de inversión del Family Office."
        ),
        can_recommend=[
            "Posicionamiento macro (risk-on/risk-off)",
            "Exposición geográfica basada en riesgo país",
            "Cobertura de escenarios geopolíticos",
            "Timing macro para entrada/salida de activos",
        ],
        can_veto=[],
        inputs=[
            "Datos macro: PIB, inflación, tasas, empleo, PMI",
            "Indicadores líderes (LEI, yield curve, spreads)",
            "Noticias y eventos geopolíticos relevantes",
            "Datos de bancos centrales (Fed, BCE, BoE)",
            "Datos de FRED, BIS, IMF, World Bank",
        ],
        outputs=[
            "Evaluación del ciclo económico actual",
            "Mapa de riesgos geopolíticos por región",
            "Impacto esperado en clases de activos",
            "Escenarios macro (base, optimista, adverso)",
        ],
        reports_to=[AgentRole.CIO, AgentRole.INVESTMENT_COMMITTEE],
        interacts_with=[
            AgentRole.FUNDAMENTAL,
            AgentRole.CREDIT_BONDS,
            AgentRole.RISK_MANAGER,
        ],
        restrictions=[
            "NO recomendar activos específicos — solo contexto macro",
            "NO hacer predicciones de precios puntuales",
            "NO ignorar eventos geopolíticos por baja probabilidad",
            "NO asumir que el régimen macro actual persiste indefinidamente",
        ],
    )


class MacroGeopoliticsAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_macro_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        macro_data = context.get("macro_data", {})
        geopolitical_events = context.get("geopolitical_events", [])
        regions = context.get("regions", ["global"])

        macro_text = ""
        if macro_data:
            for key, val in macro_data.items():
                macro_text += f"  {key}: {val}\n"

        geo_text = ""
        if geopolitical_events:
            for evt in geopolitical_events:
                geo_text += f"  - {evt}\n"

        return (
            f"ANÁLISIS MACRO/GEOPOLÍTICO: {subject}\n\n"
            f"REGIONES DE INTERÉS: {', '.join(regions)}\n\n"
            f"DATOS MACRO DISPONIBLES:\n{macro_text or '  Usar conocimiento actualizado'}\n\n"
            f"EVENTOS GEOPOLÍTICOS RELEVANTES:\n{geo_text or '  Evaluar contexto actual'}\n\n"
            f"Produce un análisis que cubra:\n"
            f"1. CICLO ECONÓMICO — ¿Dónde estamos? ¿Hacia dónde vamos?\n"
            f"2. POLÍTICA MONETARIA — Tasas, QT/QE, forward guidance\n"
            f"3. RIESGO GEOPOLÍTICO — Eventos que impactan la inversión\n"
            f"4. IMPACTO EN ACTIVOS — Cómo afecta a renta variable, fija, real assets\n"
            f"5. POSICIONAMIENTO — Risk-on vs risk-off, sectores/regiones favorecidos\n\n"
            f"Sé específico. Usa datos concretos cuando estén disponibles."
        )

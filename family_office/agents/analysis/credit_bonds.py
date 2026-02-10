"""
Agente de Crédito / Bonos
==========================
Especialista en renta fija, spreads de crédito y mercados de deuda.
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


def create_credit_contract() -> AgentContract:
    return AgentContract(
        name="Credit & Bonds Analyst",
        role=AgentRole.CREDIT_BONDS,
        layer=AgentLayer.ANALYSIS,
        specialty="Renta fija, crédito corporativo y soberano, spreads",
        primary_objective=(
            "Analizar instrumentos de renta fija (bonos soberanos, corporativos, "
            "high yield, EM debt), evaluar riesgo de crédito, duración, spreads "
            "y su impacto en la estrategia de portfolio."
        ),
        can_recommend=[
            "Posicionamiento en duración",
            "Calidad crediticia objetivo",
            "Oportunidades en spreads",
            "Instrumentos de renta fija específicos",
            "Cobertura de tasas de interés",
        ],
        can_veto=[],
        inputs=[
            "Curvas de rendimiento soberanas",
            "Spreads de crédito (IG, HY, EM)",
            "Ratings y outlooks (S&P, Moody's, Fitch)",
            "Datos de emisiones y flujos",
            "CDS spreads",
        ],
        outputs=[
            "Evaluación de riesgo de crédito",
            "Análisis de curva y duración",
            "Oportunidades en renta fija",
            "Impacto de tasas en el portfolio",
        ],
        reports_to=[AgentRole.CIO, AgentRole.INVESTMENT_COMMITTEE],
        interacts_with=[
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.RISK_MANAGER,
            AgentRole.FUNDAMENTAL,
        ],
        restrictions=[
            "NO ignorar el riesgo de duración en escenarios de tasas al alza",
            "NO equiparar investment grade con libre de riesgo",
            "NO analizar bonos sin considerar el riesgo de reinversión",
            "NO omitir el riesgo de divisa en deuda denominada en moneda extranjera",
        ],
    )


class CreditBondsAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_credit_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        instrument = context.get("instrument", "")
        yield_data = context.get("yield_data", {})
        spread_data = context.get("spread_data", {})
        rating = context.get("rating", "")
        duration = context.get("duration", "")

        yield_text = ""
        if yield_data:
            for key, val in yield_data.items():
                yield_text += f"  {key}: {val}\n"

        return (
            f"ANÁLISIS DE CRÉDITO/RENTA FIJA: {subject}\n\n"
            f"Instrumento: {instrument or 'N/A'}\n"
            f"Rating: {rating or 'N/A'}\n"
            f"Duración: {duration or 'N/A'}\n\n"
            f"DATOS DE YIELD:\n{yield_text or '  Usar datos de mercado actuales'}\n\n"
            f"Analiza:\n"
            f"1. CRÉDITO — Calidad del emisor, probabilidad de default, recovery rate\n"
            f"2. DURACIÓN — Sensibilidad a tasas, convexidad\n"
            f"3. SPREAD — vs benchmark, tendencia, valor relativo\n"
            f"4. CURVA — Posición en la curva, expectativa de movimiento\n"
            f"5. LIQUIDEZ — Profundidad del mercado, bid-ask\n"
            f"6. DIVISA — Riesgo cambiario si aplica\n"
            f"7. YIELD REAL — Ajustado por inflación esperada\n"
            f"8. RECOMENDACIÓN — Comprar/mantener/evitar con justificación\n"
        )

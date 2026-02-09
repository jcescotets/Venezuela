"""
Agente de Análisis Fundamental
===============================
Evalúa activos por su valor intrínseco: financials, moats, management, valoración.
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


def create_fundamental_contract() -> AgentContract:
    return AgentContract(
        name="Fundamental Analyst",
        role=AgentRole.FUNDAMENTAL,
        layer=AgentLayer.ANALYSIS,
        specialty="Análisis fundamental de activos (equity, private, corporate)",
        primary_objective=(
            "Evaluar el valor intrínseco de activos de inversión usando análisis "
            "de estados financieros, ventajas competitivas, calidad del management, "
            "y métricas de valoración (DCF, múltiplos, sum-of-parts)."
        ),
        can_recommend=[
            "Valoración de activos individuales",
            "Comparables y múltiplos de referencia",
            "Puntos de entrada/salida por valoración",
            "Calidad del negocio y durabilidad del moat",
        ],
        can_veto=[],
        inputs=[
            "Estados financieros (income, balance, cash flow)",
            "Métricas de la industria y comparables",
            "Datos de yfinance, Bloomberg, SEC filings",
            "Informes de analistas y guidance",
        ],
        outputs=[
            "Valoración intrínseca estimada",
            "Análisis de margen de seguridad",
            "Drivers de valor y riesgos fundamentales",
            "Nivel de convicción (alta/media/baja)",
        ],
        reports_to=[AgentRole.CIO, AgentRole.INVESTMENT_COMMITTEE],
        interacts_with=[
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.TECHNICAL_QUANT,
            AgentRole.CREDIT_BONDS,
        ],
        restrictions=[
            "NO recomendar basándose solo en momentum o precio",
            "NO ignorar la calidad del balance por un P/E atractivo",
            "NO usar proyecciones sin sensibilizar escenarios",
            "NO asumir crecimiento perpetuo sin justificación",
        ],
    )


class FundamentalAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_fundamental_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        ticker = context.get("ticker", "")
        financials = context.get("financials", {})
        industry = context.get("industry", "")
        market_cap = context.get("market_cap", "")
        price = context.get("current_price", "")

        fin_text = ""
        if financials:
            for key, val in financials.items():
                fin_text += f"  {key}: {val}\n"

        return (
            f"ANÁLISIS FUNDAMENTAL: {subject}\n\n"
            f"Ticker: {ticker or 'N/A'}\n"
            f"Industria: {industry or 'N/A'}\n"
            f"Market Cap: {market_cap or 'N/A'}\n"
            f"Precio actual: {price or 'N/A'}\n\n"
            f"DATOS FINANCIEROS:\n{fin_text or '  Usar datos públicos disponibles'}\n\n"
            f"Analiza:\n"
            f"1. CALIDAD DEL NEGOCIO — Moat, pricing power, recurrencia\n"
            f"2. FINANCIALS — Márgenes, ROIC, generación de caja, deuda\n"
            f"3. MANAGEMENT — Track record, alineación de incentivos, capital allocation\n"
            f"4. VALORACIÓN — DCF (bear/base/bull), múltiplos vs comparables\n"
            f"5. MARGEN DE SEGURIDAD — % upside/downside al precio actual\n"
            f"6. CATALIZADORES — Qué puede desbloquear valor\n"
            f"7. RIESGOS — Qué puede destruir la tesis\n\n"
            f"Nivel de convicción: indica ALTA, MEDIA o BAJA con justificación."
        )

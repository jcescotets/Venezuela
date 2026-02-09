"""
Agente Técnico / Quant
=======================
Análisis técnico de mercados y modelos cuantitativos.
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


def create_technical_contract() -> AgentContract:
    return AgentContract(
        name="Technical & Quant Analyst",
        role=AgentRole.TECHNICAL_QUANT,
        layer=AgentLayer.ANALYSIS,
        specialty="Análisis técnico de precios, momentum y modelos cuantitativos",
        primary_objective=(
            "Proveer análisis de timing, tendencias, momentum y estructura de "
            "precios para complementar el análisis fundamental con señales "
            "cuantitativas y niveles de entrada/salida."
        ),
        can_recommend=[
            "Niveles de entrada y salida técnicos",
            "Señales de momentum y cambio de tendencia",
            "Correlaciones y patrones estadísticos",
            "Sizing de posición basado en volatilidad",
        ],
        can_veto=[],
        inputs=[
            "Datos de precios históricos (OHLCV)",
            "Indicadores técnicos (RSI, MACD, Bollinger, etc.)",
            "Datos de volatilidad y opciones",
            "Flujos de fondos y sentimiento",
            "Datos de yfinance y APIs de mercado",
        ],
        outputs=[
            "Tendencia y estructura de precios",
            "Niveles técnicos clave (soporte/resistencia)",
            "Señales de momentum y divergencias",
            "Análisis de volatilidad y posicionamiento",
        ],
        reports_to=[AgentRole.CIO, AgentRole.INVESTMENT_COMMITTEE],
        interacts_with=[
            AgentRole.FUNDAMENTAL,
            AgentRole.RISK_MANAGER,
            AgentRole.PORTFOLIO_OPS,
        ],
        restrictions=[
            "NO basar recomendaciones solo en patrones chartistas subjetivos",
            "NO ignorar el contexto fundamental en las señales técnicas",
            "NO predecir precios exactos — dar rangos y probabilidades",
            "NO usar indicadores sin explicar su lógica",
        ],
    )


class TechnicalQuantAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_technical_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        ticker = context.get("ticker", "")
        price_data = context.get("price_data", {})
        indicators = context.get("indicators", {})
        timeframe = context.get("timeframe", "medio plazo (3-12 meses)")

        price_text = ""
        if price_data:
            for key, val in price_data.items():
                price_text += f"  {key}: {val}\n"

        ind_text = ""
        if indicators:
            for key, val in indicators.items():
                ind_text += f"  {key}: {val}\n"

        return (
            f"ANÁLISIS TÉCNICO/QUANT: {subject}\n\n"
            f"Ticker: {ticker or 'N/A'}\n"
            f"Timeframe: {timeframe}\n\n"
            f"DATOS DE PRECIO:\n{price_text or '  Usar datos públicos disponibles'}\n\n"
            f"INDICADORES:\n{ind_text or '  Calcular los más relevantes'}\n\n"
            f"Analiza:\n"
            f"1. TENDENCIA — Primaria, secundaria, estructura de máximos/mínimos\n"
            f"2. MOMENTUM — RSI, MACD, divergencias positivas/negativas\n"
            f"3. VOLATILIDAD — ATR, Bollinger, volatilidad histórica vs implícita\n"
            f"4. VOLUMEN — Confirmación de movimientos, distribución/acumulación\n"
            f"5. NIVELES CLAVE — Soportes, resistencias, zonas de demanda/oferta\n"
            f"6. CORRELACIONES — Con índices, sectores, otros activos del portfolio\n"
            f"7. SEÑAL — Compra/venta/espera con nivel de confianza\n\n"
            f"Indica zona óptima de entrada, stop loss sugerido y targets."
        )

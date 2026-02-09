"""
Agente Real Assets
===================
Inmobiliario, metales preciosos, commodities, alternativos.
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


def create_real_assets_contract() -> AgentContract:
    return AgentContract(
        name="Real Assets Analyst",
        role=AgentRole.REAL_ASSETS,
        layer=AgentLayer.ANALYSIS,
        specialty="Activos reales: inmobiliario, metales, commodities, alternativos",
        primary_objective=(
            "Evaluar oportunidades en activos reales como cobertura contra inflación, "
            "diversificación y generación de rentas: inmobiliario (residencial, "
            "comercial, industrial), metales preciosos, commodities y alternativos "
            "(private equity, infraestructura, crypto como activo alternativo)."
        ),
        can_recommend=[
            "Asignación a activos reales dentro del portfolio",
            "Oportunidades inmobiliarias por mercado/sector",
            "Posicionamiento en metales y commodities",
            "Vehículos de inversión alternativos",
        ],
        can_veto=[],
        inputs=[
            "Datos de mercados inmobiliarios (precios, rentas, cap rates)",
            "Precios de commodities y metales",
            "Datos de inflación y expectativas",
            "Flujos a fondos alternativos",
            "Datos de private markets (PE, VC, infra)",
        ],
        outputs=[
            "Evaluación de activos reales por categoría",
            "Yield esperado (rentas + apreciación)",
            "Análisis de liquidez y horizonte",
            "Correlación con el resto del portfolio",
        ],
        reports_to=[AgentRole.CIO, AgentRole.INVESTMENT_COMMITTEE],
        interacts_with=[
            AgentRole.MACRO_GEOPOLITICS,
            AgentRole.RISK_MANAGER,
            AgentRole.FISCAL_SPAIN,
            AgentRole.FISCAL_PORTUGAL,
        ],
        restrictions=[
            "NO ignorar la iliquidez como riesgo en activos reales",
            "NO valorar inmobiliario sin considerar costes de transacción",
            "NO recomendar commodities sin analizar el ciclo y contango/backwardation",
            "NO presentar crypto como activo seguro — siempre como alto riesgo/alternativo",
        ],
    )


class RealAssetsAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_real_assets_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        asset_type = context.get("asset_type", "general")
        location = context.get("location", "")
        market_data = context.get("market_data", {})
        inflation = context.get("inflation_expectation", "")

        mkt_text = ""
        if market_data:
            for key, val in market_data.items():
                mkt_text += f"  {key}: {val}\n"

        return (
            f"ANÁLISIS DE ACTIVOS REALES: {subject}\n\n"
            f"Tipo de activo: {asset_type}\n"
            f"Ubicación/Mercado: {location or 'Global'}\n"
            f"Expectativa de inflación: {inflation or 'N/A'}\n\n"
            f"DATOS DE MERCADO:\n{mkt_text or '  Usar datos disponibles'}\n\n"
            f"Analiza:\n"
            f"1. VALORACIÓN — ¿Está barato/caro vs históricos y fundamentals?\n"
            f"2. YIELD — Renta corriente esperada (cap rate, dividend yield, cupón)\n"
            f"3. APRECIACIÓN — Potencial de revalorización a medio/largo plazo\n"
            f"4. COBERTURA INFLACIÓN — ¿Protege efectivamente contra inflación?\n"
            f"5. LIQUIDEZ — ¿Cuánto tiempo/coste para entrar y salir?\n"
            f"6. CORRELACIÓN — Con renta variable y fija del portfolio\n"
            f"7. JURISDICCIÓN — Implicaciones fiscales y regulatorias de la ubicación\n"
            f"8. RECOMENDACIÓN — Peso sugerido en portfolio con justificación\n"
        )

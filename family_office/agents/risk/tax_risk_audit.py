"""
Tax Risk & Audit Defense
=========================
Evalúa la defendibilidad de las estructuras ante inspección fiscal.
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


def create_tax_risk_contract() -> AgentContract:
    return AgentContract(
        name="Tax Risk & Audit Defense",
        role=AgentRole.TAX_RISK_AUDIT,
        layer=AgentLayer.RISK,
        specialty="Defensa ante inspección fiscal y gestión de riesgo tributario",
        primary_objective=(
            "Evaluar la defendibilidad de cada estructura y operación ante "
            "una posible inspección fiscal (AEAT en España, IRS en US, etc.), "
            "asegurar documentación adecuada y preparar estrategia de defensa."
        ),
        can_recommend=[
            "Documentación de soporte necesaria",
            "Refuerzo de substance en entidades",
            "Restructuraciones para mejorar defendibilidad",
            "Opiniones legales preventivas (ruling requests)",
        ],
        can_veto=[],
        inputs=[
            "Estructuras fiscales propuestas y existentes",
            "Análisis de los agentes fiscales por jurisdicción",
            "Precedentes judiciales y doctrina administrativa",
            "Criterios conocidos de inspección",
        ],
        outputs=[
            "Nivel de riesgo de inspección (alto/medio/bajo)",
            "Puntos débiles de cada estructura",
            "Documentación mínima requerida",
            "Estrategia de defensa si hay inspección",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.CROSS_BORDER,
            AgentRole.RISK_MANAGER,
        ],
        restrictions=[
            "NO aprobar estructuras sin documentación de soporte",
            "NO asumir que una inspección no ocurrirá",
            "NO minimizar riesgos para facilitar operaciones",
            "NO recomendar destrucción o alteración de documentación",
        ],
    )


class TaxRiskAuditAgent(BaseAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_tax_risk_contract(), bus=bus)

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.PROPOSAL]

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        structure = context.get("structure_description", "")
        jurisdictions = context.get("jurisdictions", [])
        entities = context.get("entities", [])
        existing_docs = context.get("documentation", [])

        return (
            f"EVALUACIÓN DE RIESGO FISCAL / AUDIT DEFENSE: {subject}\n\n"
            f"ESTRUCTURA:\n{structure or 'No descrita'}\n\n"
            f"JURISDICCIONES: {', '.join(jurisdictions) if jurisdictions else 'N/A'}\n"
            f"ENTIDADES: {', '.join(entities) if entities else 'N/A'}\n"
            f"DOCUMENTACIÓN EXISTENTE: {', '.join(existing_docs) if existing_docs else 'Ninguna'}\n\n"
            f"EVALÚA:\n"
            f"1. RIESGO DE INSPECCIÓN — probabilidad y triggers\n"
            f"2. PUNTOS DÉBILES — qué atacaría un inspector\n"
            f"3. SUBSTANCE — ¿Las entidades tienen sustancia real demostrable?\n"
            f"4. DOCUMENTACIÓN — ¿Qué documentos faltan o son insuficientes?\n"
            f"5. PRECEDENTES — ¿Hay doctrina o jurisprudencia relevante?\n"
            f"6. DEFENSA — Estrategia si hay inspección\n"
            f"7. RECOMENDACIONES — Acciones para reducir riesgo\n"
            f"8. NIVEL DE RIESGO — ALTO / MEDIO / BAJO con justificación\n"
        )

"""
Agente Cross-Border / Transfer Pricing
========================================
Analiza flujos entre jurisdicciones, precios de transferencia y coherencia
de la estructura multi-jurisdiccional.
"""

from __future__ import annotations

from typing import Any

from family_office.agents.fiscal.base_fiscal import BaseFiscalAgent
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
)


def create_cross_border_contract() -> AgentContract:
    return AgentContract(
        name="Cross-Border & Transfer Pricing Advisor",
        role=AgentRole.CROSS_BORDER,
        layer=AgentLayer.FISCAL,
        specialty="Fiscalidad transfronteriza, transfer pricing, CDIs, flujos inter-sociedades",
        primary_objective=(
            "Analizar la coherencia fiscal de flujos entre jurisdicciones, "
            "evaluar precios de transferencia, verificar aplicabilidad de CDIs, "
            "y detectar riesgos de doble imposición o doble no-imposición "
            "en la estructura multi-jurisdiccional del Family Office."
        ),
        can_recommend=[
            "Rutas óptimas de flujos inter-sociedades",
            "Políticas de transfer pricing",
            "Aplicación de CDIs y directivas UE",
            "Reestructuración de flujos para eficiencia fiscal",
        ],
        can_veto=[],
        inputs=[
            "Mapa de entidades y jurisdicciones del Family Office",
            "Flujos planificados entre entidades",
            "CDIs aplicables entre jurisdicciones",
            "Evaluaciones de cada agente jurisdiccional",
        ],
        outputs=[
            "Mapa de retenciones en la cadena de flujos",
            "Análisis de transfer pricing",
            "Riesgos de doble imposición",
            "Ruta fiscal óptima para cada tipo de flujo",
        ],
        reports_to=[AgentRole.HEAD_TAX_STRATEGY],
        interacts_with=[
            AgentRole.HEAD_TAX_STRATEGY,
            AgentRole.FISCAL_SPAIN,
            AgentRole.FISCAL_PORTUGAL,
            AgentRole.FISCAL_PANAMA,
            AgentRole.FISCAL_BARBADOS,
            AgentRole.FISCAL_US,
            AgentRole.FISCAL_VENEZUELA,
        ],
        restrictions=[
            "NO recomendar flujos artificiales sin sustancia económica",
            "NO asumir treaty shopping es legítimo sin análisis de LOB/PPT",
            "NO ignorar DAC6/MDR reporting en esquemas transfronterizos",
            "NO omitir el análisis de beneficiario efectivo en flujos de dividendos",
        ],
    )


class CrossBorderAgent(BaseFiscalAgent):
    def __init__(self, bus=None):
        super().__init__(contract=create_cross_border_contract(), bus=bus)

    def get_jurisdiction(self) -> str:
        return "Cross-Border"

    def get_tax_framework(self) -> str:
        return (
            "CROSS-BORDER — MARCO DE REFERENCIA:\n"
            "• CDIs relevantes del Family Office:\n"
            "  - España-Portugal: Dividendos 10/15%, intereses 15%\n"
            "  - España-US: Dividendos 15%, intereses 10%\n"
            "  - España-Panamá: NO hay CDI vigente\n"
            "  - España-Barbados: Verificar existencia/términos\n"
            "  - España-Venezuela: NO hay CDI vigente\n"
            "• Directivas UE (vía Portugal):\n"
            "  - Directiva Madre-Filial: Exención WHT dividendos intra-UE\n"
            "  - Directiva Intereses-Royalties: Exención WHT intra-UE\n"
            "• Transfer Pricing:\n"
            "  - Principio arm's length (OCDE)\n"
            "  - Documentación obligatoria (masterfile + local file)\n"
            "  - Country-by-Country Reporting si procede\n"
            "• Anti-avoidance:\n"
            "  - ATAD I y II (UE) — vía España y Portugal\n"
            "  - LOB / PPT en CDIs post-MLI\n"
            "  - DAC6 / MDR: Reporting de esquemas transfronterizos\n"
            "  - Beneficiario efectivo: Test en cada eslabón\n"
            "• CRS: Intercambio automático entre todas las jurisdicciones\n"
            "• FATCA: Reporting de cuentas con nexo US"
        )

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        flow_from = context.get("flow_from", "")
        flow_to = context.get("flow_to", "")
        flow_type = context.get("flow_type", "dividendos")
        amount = context.get("amount_usd", "no especificado")
        entities = context.get("entity_chain", [])
        jurisdictional_reports = context.get("jurisdictional_reports", [])

        entity_text = ""
        if entities:
            for e in entities:
                entity_text += f"  → {e}\n"

        jr_text = ""
        if jurisdictional_reports:
            for jr in jurisdictional_reports:
                if isinstance(jr, dict):
                    jr_text += f"\n  [{jr.get('jurisdiction')}]: {jr.get('summary', 'N/A')[:200]}\n"

        return (
            f"ANÁLISIS CROSS-BORDER: {subject}\n\n"
            f"FLUJO: {flow_from or '?'} → {flow_to or '?'}\n"
            f"TIPO: {flow_type}\n"
            f"MONTO: USD {amount}\n\n"
            f"CADENA DE ENTIDADES:\n{entity_text or '  No definida'}\n\n"
            f"ANÁLISIS JURISDICCIONALES:{jr_text or '  Pendientes'}\n\n"
            f"EVALÚA:\n"
            f"1. RETENCIONES — En CADA eslabón de la cadena\n"
            f"2. CDI APLICABLE — ¿Hay CDI? ¿Se cumplen condiciones (LOB/PPT)?\n"
            f"3. BENEFICIARIO EFECTIVO — ¿Cada entidad pasa el test?\n"
            f"4. TRANSFER PRICING — ¿Los precios son arm's length?\n"
            f"5. SUBSTANCE — ¿Cada entidad tiene sustancia suficiente?\n"
            f"6. DOBLE IMPOSICIÓN — ¿Hay riesgo? ¿Se puede mitigar?\n"
            f"7. REPORTING — ¿Qué obligaciones DAC6/CRS/FATCA aplican?\n"
            f"8. RUTA ÓPTIMA — ¿Cuál es la ruta fiscal más eficiente y defendible?\n\n"
            f"La ruta debe ser DEFENDIBLE ante inspección. No optimizar a costa de riesgo."
        )

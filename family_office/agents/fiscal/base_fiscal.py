"""
BaseFiscalAgent — Clase base para todos los agentes fiscales jurisdiccionales.
Implementa la lógica común de evaluación fiscal.
"""

from __future__ import annotations

from abc import abstractmethod
from typing import Any

from family_office.core.base_agent import BaseAgent
from family_office.core.models import (
    AgentContract,
    FiscalImpact,
    MessageType,
)


class BaseFiscalAgent(BaseAgent):
    """
    Base para agentes fiscales.
    Cada jurisdicción hereda de aquí y define su normativa específica.
    """

    def _subscribed_message_types(self) -> list[MessageType]:
        return [MessageType.ANALYSIS_REQUEST, MessageType.PROPOSAL]

    @abstractmethod
    def get_jurisdiction(self) -> str:
        """Nombre de la jurisdicción que cubre este agente."""
        ...

    @abstractmethod
    def get_tax_framework(self) -> str:
        """Descripción del marco fiscal de la jurisdicción para el system prompt."""
        ...

    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        amount = context.get("amount_usd", "no especificado")
        asset_class = context.get("asset_class", "no especificado")
        vehicle = context.get("holding_vehicle", "directo")
        income_type = context.get("income_type", "mixto (rentas + ganancias de capital)")
        source_jurisdiction = context.get("source_jurisdiction", "")
        destination_jurisdiction = context.get("destination_jurisdiction", "")

        return (
            f"EVALUACIÓN FISCAL — {self.get_jurisdiction()}: {subject}\n\n"
            f"MARCO NORMATIVO DE REFERENCIA:\n{self.get_tax_framework()}\n\n"
            f"PARÁMETROS DE LA OPERACIÓN:\n"
            f"  Monto: USD {amount}\n"
            f"  Clase de activo: {asset_class}\n"
            f"  Vehículo: {vehicle}\n"
            f"  Tipo de renta: {income_type}\n"
            f"  Origen: {source_jurisdiction or self.get_jurisdiction()}\n"
            f"  Destino: {destination_jurisdiction or 'España (residencia)'}\n\n"
            f"EVALÚA:\n"
            f"1. TIPO IMPOSITIVO APLICABLE — sobre esta operación en esta jurisdicción\n"
            f"2. RETENCIONES — withholding tax en origen y destino\n"
            f"3. RIESGO CFC — ¿podría España imputar esta renta como CFC?\n"
            f"4. ESTABLECIMIENTO PERMANENTE — ¿riesgo de EP en esta jurisdicción?\n"
            f"5. SUBSTANCE — ¿el vehículo tiene sustancia suficiente aquí?\n"
            f"6. CDI — ¿hay convenio de doble imposición? ¿Aplica? ¿Condiciones?\n"
            f"7. RETORNO NETO — después de impuestos en ESTA jurisdicción\n"
            f"8. ALERTAS — cualquier riesgo regulatorio específico\n\n"
            f"Sé preciso con las tasas. Cita la normativa cuando sea posible."
        )

    async def evaluate_fiscal_impact(
        self, subject: str, context: dict[str, Any]
    ) -> FiscalImpact:
        """Produce una evaluación fiscal estructurada."""
        report = await self.analyze(subject, context)

        # Default impact — subclasses override with jurisdiction-specific logic
        gross_return = context.get("expected_gross_return_pct", 0.0)
        effective_rate = self._estimate_effective_rate(context)

        return FiscalImpact(
            jurisdiction=self.get_jurisdiction(),
            gross_return_pct=gross_return,
            tax_rate_effective=effective_rate,
            net_return_pct=gross_return * (1 - effective_rate / 100),
            cfc_risk=self._assess_cfc_risk(context),
            permanent_establishment_risk=self._assess_pe_risk(context),
            substance_risk=self._assess_substance_risk(context),
            double_taxation_risk=self._assess_dti_risk(context),
            notes=[report.summary[:300]],
        )

    def _estimate_effective_rate(self, context: dict[str, Any]) -> float:
        """Tasa efectiva estimada — cada jurisdicción override."""
        return 25.0  # Default conservador

    def _assess_cfc_risk(self, context: dict[str, Any]) -> bool:
        return False

    def _assess_pe_risk(self, context: dict[str, Any]) -> bool:
        return False

    def _assess_substance_risk(self, context: dict[str, Any]) -> bool:
        return False

    def _assess_dti_risk(self, context: dict[str, Any]) -> bool:
        return False

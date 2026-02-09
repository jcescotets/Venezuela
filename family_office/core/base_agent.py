"""
BaseAgent — Clase base de la que heredan TODOS los agentes del Family Office.
Implementa el contrato operativo (Instrucción 4) y la integración con el bus.
"""

from __future__ import annotations

import logging
from abc import ABC, abstractmethod
from typing import Any, Optional

from family_office.core.llm_client import call_llm
from family_office.core.models import (
    AgentContract,
    AgentLayer,
    AgentRole,
    AnalysisReport,
    Message,
    MessageType,
    VetoDecision,
)

logger = logging.getLogger(__name__)


class BaseAgent(ABC):
    """
    Agente base del Family Office.

    Cada agente:
    - Tiene un contrato que define su rol, capacidades y límites
    - Se comunica exclusivamente a través del MessageBus
    - Puede producir AnalysisReports
    - Puede (si autorizado) emitir vetos
    - Llama al LLM con su system prompt especializado
    """

    def __init__(self, contract: AgentContract, bus=None):
        self.contract = contract
        self.bus = bus
        self.logger = logging.getLogger(f"agent.{contract.role.value}")
        self._analysis_cache: dict[str, AnalysisReport] = {}

    @property
    def role(self) -> AgentRole:
        return self.contract.role

    @property
    def name(self) -> str:
        return self.contract.name

    @property
    def layer(self) -> AgentLayer:
        return self.contract.layer

    def set_bus(self, bus):
        """Conecta el agente al bus de mensajes."""
        self.bus = bus
        # Subscribe to direct messages
        bus.subscribe_direct(self.role, self.handle_message)
        # Subscribe to broadcasts this agent cares about
        for msg_type in self._subscribed_message_types():
            bus.subscribe_type(msg_type, self.role, self.handle_message)

    def _subscribed_message_types(self) -> list[MessageType]:
        """Tipos de mensaje a los que este agente se suscribe. Override en subclases."""
        return [MessageType.ANALYSIS_REQUEST, MessageType.DATA_UPDATE]

    # ------------------------------------------------------------------
    # Core: System prompt
    # ------------------------------------------------------------------

    def build_system_prompt(self) -> str:
        """Construye el system prompt del agente basado en su contrato."""
        c = self.contract
        restrictions = "\n".join(f"- {r}" for r in c.restrictions) if c.restrictions else "Ninguna específica"
        return (
            f"Eres {c.name}, {c.specialty} del Family Office.\n"
            f"Capa: {c.layer.value}\n"
            f"Rol: {c.role.value}\n\n"
            f"OBJETIVO PRINCIPAL: {c.primary_objective}\n\n"
            f"PUEDES RECOMENDAR:\n"
            + "\n".join(f"- {r}" for r in c.can_recommend)
            + f"\n\nPUEDES VETAR:\n"
            + "\n".join(f"- {v}" for v in c.can_veto) if c.can_veto else "- No tienes poder de veto"
            + f"\n\nRESTRICCIONES (lo que NO puedes hacer):\n{restrictions}\n\n"
            f"REPORTAS A: {', '.join(r.value for r in c.reports_to)}\n"
            f"INTERACTÚAS CON: {', '.join(r.value for r in c.interacts_with)}\n\n"
            f"REGLAS GENERALES:\n"
            f"- Responde SOLO dentro de tu especialidad\n"
            f"- Sé ejecutivo y concreto, nunca genérico\n"
            f"- Usa lenguaje profesional de inversión\n"
            f"- Justifica toda afirmación con datos o razonamiento\n"
            f"- Si no tienes información suficiente, dilo explícitamente\n"
            f"- NO hagas recomendaciones fuera de tu ámbito\n"
        )

    # ------------------------------------------------------------------
    # Core: Analysis
    # ------------------------------------------------------------------

    async def analyze(self, subject: str, context: dict[str, Any] | None = None) -> AnalysisReport:
        """Produce un análisis usando el LLM con el system prompt del agente."""
        self.logger.info(f"Analyzing: {subject}")

        user_prompt = self._build_analysis_prompt(subject, context or {})
        response = await call_llm(
            system_prompt=self.build_system_prompt(),
            user_prompt=user_prompt,
        )

        report = self._parse_analysis(subject, response, context)
        self._analysis_cache[report.id] = report

        # Publish to bus
        if self.bus:
            await self.bus.publish(Message(
                type=MessageType.ANALYSIS_REPORT,
                sender=self.role,
                payload=report.model_dump(mode="json"),
                correlation_id=context.get("correlation_id") if context else None,
            ))

        return report

    @abstractmethod
    def _build_analysis_prompt(self, subject: str, context: dict[str, Any]) -> str:
        """Construye el prompt específico para el análisis. Cada agente lo implementa."""
        ...

    def _parse_analysis(
        self, subject: str, llm_response: str, context: dict[str, Any] | None
    ) -> AnalysisReport:
        """Parsea la respuesta del LLM en un AnalysisReport estructurado."""
        # Default parsing — subclases pueden override para parsing más sofisticado
        lines = llm_response.strip().split("\n")
        key_findings = []
        risks = []
        recommendation = None

        section = None
        for line in lines:
            stripped = line.strip()
            lower = stripped.lower()
            if "hallazgo" in lower or "finding" in lower or "conclusi" in lower:
                section = "findings"
                continue
            elif "riesgo" in lower or "risk" in lower:
                section = "risks"
                continue
            elif "recomend" in lower:
                section = "recommendation"
                continue

            if stripped.startswith(("-", "*", "•")) and len(stripped) > 2:
                item = stripped.lstrip("-*• ").strip()
                if section == "findings":
                    key_findings.append(item)
                elif section == "risks":
                    risks.append(item)
            elif section == "recommendation" and stripped:
                recommendation = (recommendation or "") + " " + stripped

        return AnalysisReport(
            agent_role=self.role,
            subject=subject,
            summary=llm_response[:500],
            conviction_level=0.5,  # Will be refined by specific agents
            key_findings=key_findings or [llm_response[:200]],
            risks_identified=risks,
            recommendation=recommendation,
            raw_data=context or {},
        )

    # ------------------------------------------------------------------
    # Veto capability
    # ------------------------------------------------------------------

    async def issue_veto(
        self, proposal_id: str, veto_type, justification: str, severity: float = 0.8
    ) -> Optional[VetoDecision]:
        """Emite un veto si el agente tiene autorización."""
        if not self.contract.can_veto:
            self.logger.warning(f"{self.name} attempted veto but has no veto power")
            return None

        veto = VetoDecision(
            agent_role=self.role,
            proposal_id=proposal_id,
            veto_type=veto_type,
            justification=justification,
            severity=severity,
        )

        if self.bus:
            await self.bus.publish(Message(
                type=MessageType.VETO,
                sender=self.role,
                payload=veto.model_dump(mode="json"),
                correlation_id=proposal_id,
            ))

        self.logger.warning(f"VETO issued on {proposal_id}: {justification[:100]}")
        return veto

    # ------------------------------------------------------------------
    # Message handling
    # ------------------------------------------------------------------

    async def handle_message(self, message: Message):
        """Maneja mensajes recibidos del bus. Override en subclases para lógica específica."""
        self.logger.debug(f"Received {message.type.value} from {message.sender.value}")

    # ------------------------------------------------------------------
    # Repr
    # ------------------------------------------------------------------

    def __repr__(self) -> str:
        return f"<Agent:{self.contract.name} role={self.role.value} layer={self.layer.value}>"

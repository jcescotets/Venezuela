"""
AgentRegistry — Registro central de todos los agentes activos.
Es el "directorio corporativo" de la organización.
"""

from __future__ import annotations

import logging
from typing import Optional

from family_office.core.base_agent import BaseAgent
from family_office.core.message_bus import MessageBus
from family_office.core.models import AgentLayer, AgentRole

logger = logging.getLogger(__name__)


class AgentRegistry:
    """
    Registro centralizado de agentes.
    - Registra agentes por rol
    - Conecta agentes al bus de mensajes
    - Permite consultar agentes por capa, rol, o capacidad
    """

    def __init__(self, bus: MessageBus):
        self.bus = bus
        self._agents: dict[AgentRole, BaseAgent] = {}

    def register(self, agent: BaseAgent):
        """Registra un agente y lo conecta al bus."""
        if agent.role in self._agents:
            raise ValueError(f"Agent with role {agent.role.value} already registered")
        self._agents[agent.role] = agent
        agent.set_bus(self.bus)
        logger.info(f"Registered: {agent}")

    def get(self, role: AgentRole) -> Optional[BaseAgent]:
        return self._agents.get(role)

    def get_by_layer(self, layer: AgentLayer) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.layer == layer]

    def get_with_veto_power(self) -> list[BaseAgent]:
        return [a for a in self._agents.values() if a.contract.can_veto]

    def get_analysis_agents(self) -> list[BaseAgent]:
        return self.get_by_layer(AgentLayer.ANALYSIS)

    def get_fiscal_agents(self) -> list[BaseAgent]:
        return self.get_by_layer(AgentLayer.FISCAL)

    def all_agents(self) -> list[BaseAgent]:
        return list(self._agents.values())

    @property
    def agent_count(self) -> int:
        return len(self._agents)

    def summary(self) -> str:
        """Resumen del estado organizativo."""
        lines = ["═══ FAMILY OFFICE — ORGANIZACIÓN AGÉNTICA ═══\n"]
        for layer in AgentLayer:
            agents = self.get_by_layer(layer)
            if agents:
                lines.append(f"▸ {layer.value.upper()} ({len(agents)} agentes)")
                for a in agents:
                    veto = " [VETO]" if a.contract.can_veto else ""
                    lines.append(f"    ├─ {a.name} ({a.role.value}){veto}")
                lines.append("")
        lines.append(f"Total: {self.agent_count} agentes activos")
        return "\n".join(lines)

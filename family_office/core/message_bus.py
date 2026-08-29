"""
Message Bus — Sistema de comunicación inter-agentes.
Los agentes NO se comunican directamente; todo pasa por el bus.
Esto garantiza que ningún agente tiene visión total del sistema.
"""

from __future__ import annotations

import asyncio
import logging
from collections import defaultdict
from typing import Any, Callable, Coroutine

from family_office.core.models import AgentRole, Message, MessageType

logger = logging.getLogger(__name__)

Subscriber = Callable[[Message], Coroutine[Any, Any, None]]


class MessageBus:
    """
    Bus centralizado de mensajes.
    - Soporta suscripción por tipo de mensaje y/o por agente destinatario
    - Los mensajes broadcast (recipient=None) llegan a todos los suscriptores del tipo
    - Los mensajes dirigidos solo llegan al agente destinatario
    """

    def __init__(self):
        self._subscribers_by_type: dict[MessageType, list[tuple[AgentRole, Subscriber]]] = defaultdict(list)
        self._subscribers_by_role: dict[AgentRole, list[Subscriber]] = defaultdict(list)
        self._message_log: list[Message] = []
        self._lock = asyncio.Lock()

    def subscribe_type(self, msg_type: MessageType, role: AgentRole, handler: Subscriber):
        """Suscribe un agente a un tipo de mensaje."""
        self._subscribers_by_type[msg_type].append((role, handler))
        logger.debug(f"{role.value} subscribed to {msg_type.value}")

    def subscribe_direct(self, role: AgentRole, handler: Subscriber):
        """Suscribe un agente a mensajes dirigidos directamente a él."""
        self._subscribers_by_role[role].append(handler)
        logger.debug(f"{role.value} subscribed to direct messages")

    async def publish(self, message: Message):
        """Publica un mensaje en el bus."""
        async with self._lock:
            self._message_log.append(message)

        logger.info(
            f"[BUS] {message.sender.value} -> "
            f"{'BROADCAST' if message.recipient is None else message.recipient.value} "
            f"| {message.type.value}"
        )

        tasks = []

        # Deliver to type subscribers
        if message.type in self._subscribers_by_type:
            for role, handler in self._subscribers_by_type[message.type]:
                # Don't echo back to sender
                if role != message.sender:
                    if message.recipient is None or message.recipient == role:
                        tasks.append(self._safe_deliver(handler, message))

        # Deliver to direct subscribers
        if message.recipient and message.recipient in self._subscribers_by_role:
            for handler in self._subscribers_by_role[message.recipient]:
                tasks.append(self._safe_deliver(handler, message))

        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_deliver(self, handler: Subscriber, message: Message):
        try:
            await handler(message)
        except Exception as e:
            logger.error(f"Error delivering message {message.id}: {e}")

    def get_message_log(
        self,
        msg_type: MessageType | None = None,
        sender: AgentRole | None = None,
        correlation_id: str | None = None,
        limit: int = 100,
    ) -> list[Message]:
        """Consulta el log de mensajes con filtros opcionales."""
        results = self._message_log
        if msg_type:
            results = [m for m in results if m.type == msg_type]
        if sender:
            results = [m for m in results if m.sender == sender]
        if correlation_id:
            results = [m for m in results if m.correlation_id == correlation_id]
        return results[-limit:]

    def clear_log(self):
        self._message_log.clear()

"""
Pipeline Events — Sistema de eventos en tiempo real para el pipeline.
Permite a los clientes (dashboard) recibir actualizaciones en vivo
del progreso de cada fase del pipeline de decisión.
"""

from __future__ import annotations

import asyncio
import json
import logging
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Callable, Coroutine

logger = logging.getLogger(__name__)


class PipelinePhase(str, Enum):
    STARTED = "started"
    ANALYSIS_RUNNING = "analysis_running"
    ANALYSIS_AGENT_DONE = "analysis_agent_done"
    ANALYSIS_COMPLETE = "analysis_complete"
    FISCAL_RUNNING = "fiscal_running"
    FISCAL_AGENT_DONE = "fiscal_agent_done"
    FISCAL_COMPLETE = "fiscal_complete"
    COMMITTEE_DEBATE = "committee_debate"
    COMMITTEE_COMPLETE = "committee_complete"
    VETO_EVALUATION = "veto_evaluation"
    VETO_COMPLETE = "veto_complete"
    CIO_SYNTHESIS = "cio_synthesis"
    CIO_COMPLETE = "cio_complete"
    VALIDATION = "validation"
    COMPLETE = "complete"
    ERROR = "error"


EventHandler = Callable[[dict[str, Any]], Coroutine[Any, Any, None]]


class PipelineEventEmitter:
    """
    Emite eventos de progreso del pipeline.
    Los clientes WebSocket se suscriben para recibir actualizaciones en tiempo real.
    """

    def __init__(self):
        self._subscribers: list[EventHandler] = []
        self._event_log: list[dict[str, Any]] = []

    def subscribe(self, handler: EventHandler):
        self._subscribers.append(handler)

    def unsubscribe(self, handler: EventHandler):
        self._subscribers = [s for s in self._subscribers if s is not handler]

    async def emit(
        self,
        proposal_id: str,
        phase: PipelinePhase,
        detail: str = "",
        progress_pct: float = 0.0,
        data: dict[str, Any] | None = None,
    ):
        event = {
            "type": "pipeline_progress",
            "proposal_id": proposal_id,
            "phase": phase.value,
            "detail": detail,
            "progress_pct": round(progress_pct, 1),
            "data": data or {},
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._event_log.append(event)

        tasks = []
        for handler in self._subscribers:
            tasks.append(self._safe_emit(handler, event))
        if tasks:
            await asyncio.gather(*tasks)

    async def _safe_emit(self, handler: EventHandler, event: dict[str, Any]):
        try:
            await handler(event)
        except Exception as e:
            logger.error(f"Event handler error: {e}")

    def get_event_log(self, proposal_id: str | None = None) -> list[dict[str, Any]]:
        if proposal_id:
            return [e for e in self._event_log if e["proposal_id"] == proposal_id]
        return self._event_log.copy()

    def clear_log(self):
        self._event_log.clear()


# Global singleton for the application
pipeline_events = PipelineEventEmitter()

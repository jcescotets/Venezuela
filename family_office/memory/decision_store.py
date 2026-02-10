"""
Decision Store — Persistencia de decisiones del Family Office.
Implementa la Instrucción 9: Memoria del Sistema.

Almacena:
- Historial de decisiones
- Supuestos utilizados
- Resultados (qué salió bien / mal)
- Cambios de criterio
- Alertas de errores repetidos
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Optional

from family_office.config.settings import MEMORY_DIR
from family_office.core.models import (
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
    VetoDecision,
)

logger = logging.getLogger(__name__)


class DecisionStore:
    """Almacena y consulta el historial de decisiones."""

    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or MEMORY_DIR / "decisions"
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._index_path = self.storage_dir / "index.json"
        self._index: list[dict[str, Any]] = self._load_index()

    def _load_index(self) -> list[dict[str, Any]]:
        if self._index_path.exists():
            return json.loads(self._index_path.read_text())
        return []

    def _save_index(self):
        self._index_path.write_text(json.dumps(self._index, indent=2, default=str))

    def store_decision(
        self,
        proposal: InvestmentProposal,
        pipeline_result: dict[str, Any],
        committee_decision: Optional[CommitteeDecision] = None,
    ) -> str:
        """Almacena una decisión completa."""
        record = {
            "id": proposal.id,
            "title": proposal.title,
            "asset_class": proposal.asset_class,
            "amount_usd": proposal.amount_usd,
            "jurisdiction": proposal.jurisdiction,
            "status": proposal.status.value,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "analyses_count": len(proposal.analyses),
            "vetoes_count": len(proposal.vetoes),
            "vetoes": [v.model_dump(mode="json") for v in proposal.vetoes],
            "assumptions": self._extract_assumptions(pipeline_result),
        }

        if committee_decision:
            record["committee"] = committee_decision.model_dump(mode="json")

        # Save full record
        record_path = self.storage_dir / f"{proposal.id}.json"
        record_path.write_text(json.dumps(record, indent=2, default=str))

        # Update index
        self._index.append({
            "id": proposal.id,
            "title": proposal.title,
            "status": proposal.status.value,
            "amount_usd": proposal.amount_usd,
            "timestamp": record["timestamp"],
        })
        self._save_index()

        logger.info(f"Decision stored: {proposal.id} — {proposal.title}")
        return proposal.id

    def store_outcome(
        self,
        decision_id: str,
        outcome: str,
        actual_return_pct: float | None = None,
        lessons: list[str] | None = None,
    ):
        """Registra el resultado real de una decisión (post-facto)."""
        record_path = self.storage_dir / f"{decision_id}.json"
        if not record_path.exists():
            logger.warning(f"Decision {decision_id} not found")
            return

        record = json.loads(record_path.read_text())
        record["outcome"] = {
            "description": outcome,
            "actual_return_pct": actual_return_pct,
            "lessons": lessons or [],
            "recorded_at": datetime.now(timezone.utc).isoformat(),
        }
        record_path.write_text(json.dumps(record, indent=2, default=str))

        # Update index
        for entry in self._index:
            if entry["id"] == decision_id:
                entry["has_outcome"] = True
                break
        self._save_index()

    def get_decision(self, decision_id: str) -> dict[str, Any] | None:
        record_path = self.storage_dir / f"{decision_id}.json"
        if record_path.exists():
            return json.loads(record_path.read_text())
        return None

    def get_all_decisions(self, status: str | None = None) -> list[dict[str, Any]]:
        results = self._index
        if status:
            results = [d for d in results if d.get("status") == status]
        return results

    def get_past_mistakes(self) -> list[dict[str, Any]]:
        """Recupera decisiones con outcomes negativos para aprendizaje."""
        mistakes = []
        for entry in self._index:
            record = self.get_decision(entry["id"])
            if record and record.get("outcome"):
                outcome = record["outcome"]
                if outcome.get("actual_return_pct") is not None:
                    if outcome["actual_return_pct"] < 0:
                        mistakes.append({
                            "id": record["id"],
                            "title": record["title"],
                            "actual_return": outcome["actual_return_pct"],
                            "lessons": outcome.get("lessons", []),
                        })
        return mistakes

    def check_repeated_patterns(self, proposal: InvestmentProposal) -> list[str]:
        """Alerta si la propuesta repite patrones de errores pasados."""
        alerts = []
        mistakes = self.get_past_mistakes()

        for m in mistakes:
            record = self.get_decision(m["id"])
            if record:
                if record.get("asset_class") == proposal.asset_class:
                    alerts.append(
                        f"⚠ Inversión similar en {proposal.asset_class} "
                        f"tuvo resultado negativo ({m['actual_return']:.1f}%): "
                        f"{m['title']}. Lecciones: {'; '.join(m.get('lessons', []))}"
                    )
                if record.get("jurisdiction") == proposal.jurisdiction:
                    for lesson in m.get("lessons", []):
                        alerts.append(
                            f"⚠ Lección previa en {proposal.jurisdiction}: {lesson}"
                        )

        return alerts

    def _extract_assumptions(self, result: dict[str, Any]) -> list[str]:
        assumptions = []
        cio = result.get("cio_synthesis")
        if cio and hasattr(cio, "cio_synthesis"):
            text = cio.cio_synthesis
            for line in text.split("\n"):
                lower = line.lower()
                if any(kw in lower for kw in ["asume", "supone", "assume", "supuesto"]):
                    assumptions.append(line.strip())
        return assumptions

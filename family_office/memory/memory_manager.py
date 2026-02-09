"""
Memory Manager — Gestión de la memoria organizativa del Family Office.
Implementa la Instrucción 9: Organización viva.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from family_office.config.settings import MEMORY_DIR

logger = logging.getLogger(__name__)


class MemoryManager:
    """
    Gestiona la memoria del Family Office:
    - Criterios de inversión y cambios
    - Alertas recurrentes
    - Contexto macroeconómico recordado
    - Preferencias del Principal
    """

    def __init__(self, storage_dir: Path | None = None):
        self.storage_dir = storage_dir or MEMORY_DIR
        self.storage_dir.mkdir(parents=True, exist_ok=True)
        self._criteria_path = self.storage_dir / "investment_criteria.json"
        self._alerts_path = self.storage_dir / "recurring_alerts.json"
        self._preferences_path = self.storage_dir / "principal_preferences.json"
        self._context_path = self.storage_dir / "macro_context.json"

    # ─── Investment Criteria ───────────────────────────────────
    def get_criteria(self) -> dict[str, Any]:
        if self._criteria_path.exists():
            return json.loads(self._criteria_path.read_text())
        return self._default_criteria()

    def update_criteria(self, key: str, value: Any, reason: str):
        criteria = self.get_criteria()
        old_value = criteria.get(key)
        criteria[key] = value
        criteria.setdefault("change_log", []).append({
            "key": key,
            "old_value": old_value,
            "new_value": value,
            "reason": reason,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        })
        self._criteria_path.write_text(json.dumps(criteria, indent=2, default=str))
        logger.info(f"Criteria updated: {key} = {value} (reason: {reason})")

    def _default_criteria(self) -> dict[str, Any]:
        return {
            "risk_tolerance": "moderate",
            "target_return_annual_pct": 8.0,
            "max_drawdown_pct": 15.0,
            "liquidity_minimum_pct": 20.0,
            "tax_efficiency_priority": "high",
            "esg_mandate": False,
            "excluded_sectors": [],
            "preferred_jurisdictions": [
                "España", "Portugal", "Estados Unidos", "Panamá", "Barbados"
            ],
            "change_log": [],
        }

    # ─── Recurring Alerts ─────────────────────────────────────
    def get_alerts(self) -> list[dict[str, Any]]:
        if self._alerts_path.exists():
            return json.loads(self._alerts_path.read_text())
        return []

    def add_alert(self, alert_type: str, message: str, source: str):
        alerts = self.get_alerts()
        alerts.append({
            "type": alert_type,
            "message": message,
            "source": source,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "resolved": False,
        })
        self._alerts_path.write_text(json.dumps(alerts, indent=2, default=str))

    def resolve_alert(self, index: int):
        alerts = self.get_alerts()
        if 0 <= index < len(alerts):
            alerts[index]["resolved"] = True
            alerts[index]["resolved_at"] = datetime.now(timezone.utc).isoformat()
            self._alerts_path.write_text(json.dumps(alerts, indent=2, default=str))

    # ─── Principal Preferences ────────────────────────────────
    def get_preferences(self) -> dict[str, Any]:
        if self._preferences_path.exists():
            return json.loads(self._preferences_path.read_text())
        return {
            "communication_style": "executive",
            "detail_level": "high",
            "language": "es",
            "fiscal_residence": "España",
            "holding_structures": {
                "portugal_lda": True,
                "panama_sem": True,
                "barbados_ibc": True,
            },
        }

    def update_preference(self, key: str, value: Any):
        prefs = self.get_preferences()
        prefs[key] = value
        self._preferences_path.write_text(json.dumps(prefs, indent=2, default=str))

    # ─── Macro Context ────────────────────────────────────────
    def get_macro_context(self) -> dict[str, Any]:
        if self._context_path.exists():
            return json.loads(self._context_path.read_text())
        return {}

    def update_macro_context(self, data: dict[str, Any]):
        context = self.get_macro_context()
        context.update(data)
        context["last_updated"] = datetime.now(timezone.utc).isoformat()
        self._context_path.write_text(json.dumps(context, indent=2, default=str))

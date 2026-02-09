"""
Decision Pipeline — Implementa la Instrucción 5: Regla de Decisión
====================================================================
Ninguna decisión de inversión es válida si no cumple TODAS las condiciones:
1. Ha sido analizada por los agentes relevantes
2. Tiene impacto financiero esperado
3. Tiene impacto fiscal neto post-impuestos
4. Ha sido evaluada por el Risk Manager
5. Ha pasado por el Comité de Inversión
"""

from __future__ import annotations

import logging
from datetime import datetime, timezone
from typing import Any

from family_office.core.models import (
    AgentRole,
    CommitteeDecision,
    DecisionStatus,
    InvestmentProposal,
)
from family_office.core.registry import AgentRegistry
from family_office.pipeline.debate_engine import DebateEngine
from family_office.pipeline.veto_gate import VetoGate

logger = logging.getLogger(__name__)


class DecisionPipeline:
    """
    Pipeline completo de decisión del Family Office.

    Fases:
    1. ANÁLISIS — Agentes de análisis evalúan independientemente
    2. FISCAL — Agentes fiscales evalúan impacto por jurisdicción
    3. DEBATE — Investment Committee sintetiza
    4. RIESGO — Risk Manager y Head of Tax evalúan vetos
    5. SÍNTESIS — CIO produce recomendación final
    6. VALIDACIÓN — Se verifica que todas las condiciones se cumplen
    7. PRESENTACIÓN — Se presenta al Principal para decisión
    """

    def __init__(self, registry: AgentRegistry):
        self.registry = registry
        self.debate_engine = DebateEngine(registry)
        self.veto_gate = VetoGate(registry)
        self._pipeline_log: list[dict[str, Any]] = []

    async def process_proposal(
        self,
        proposal: InvestmentProposal,
        portfolio: dict[str, Any] | None = None,
        context: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """
        Procesa una propuesta de inversión a través del pipeline completo.
        Devuelve un resultado estructurado para el Principal.
        """
        portfolio = portfolio or {}
        context = context or {}
        result = {
            "proposal": proposal,
            "phases": {},
            "vetoes": [],
            "committee_decision": None,
            "cio_synthesis": None,
            "status": DecisionStatus.ANALYZING,
            "ready_for_principal": False,
        }

        self._log_phase(proposal.id, "START", "Pipeline initiated")
        proposal.status = DecisionStatus.ANALYZING

        # ═══════════════════════════════════════════════════════
        # FASE 1 & 2: Análisis independiente + Fiscal (paralelo)
        # ═══════════════════════════════════════════════════════
        try:
            analysis_reports, fiscal_reports, committee_decision = (
                await self.debate_engine.full_debate(proposal, context)
            )

            proposal.analyses = analysis_reports
            result["phases"]["analysis"] = {
                "count": len(analysis_reports),
                "agents": [r.agent_role.value for r in analysis_reports],
            }
            result["phases"]["fiscal"] = {
                "count": len(fiscal_reports),
                "agents": [r.agent_role.value for r in fiscal_reports],
            }
            result["committee_decision"] = committee_decision

            self._log_phase(
                proposal.id, "ANALYSIS_COMPLETE",
                f"{len(analysis_reports)} analysis + {len(fiscal_reports)} fiscal reports"
            )
        except Exception as e:
            logger.error(f"Analysis phase failed: {e}")
            result["status"] = DecisionStatus.REJECTED
            result["error"] = str(e)
            return result

        # ═══════════════════════════════════════════════════════
        # FASE 3: Evaluación de vetos (Risk Manager + Head Tax)
        # ═══════════════════════════════════════════════════════
        try:
            # Risk veto
            risk_vetoes = await self.veto_gate.evaluate_risk_veto(proposal, portfolio)
            proposal.vetoes.extend(risk_vetoes)

            # Tax veto — using the fiscal analysis summary
            fiscal_summary = "\n".join(
                r.summary for r in fiscal_reports if r.summary
            )
            tax_vetoes = await self.veto_gate.evaluate_tax_veto(proposal, fiscal_summary)
            proposal.vetoes.extend(tax_vetoes)

            result["vetoes"] = proposal.vetoes
            veto_check = self.veto_gate.check_vetoes(proposal)
            result["veto_check"] = veto_check

            self._log_phase(
                proposal.id, "VETO_CHECK",
                f"Risk vetoes: {len(risk_vetoes)}, Tax vetoes: {len(tax_vetoes)}"
            )

            if veto_check["blocked"]:
                proposal.status = DecisionStatus.VETOED
                result["status"] = DecisionStatus.VETOED
                self._log_phase(proposal.id, "VETOED", veto_check["veto_summary"])
                # Don't return — still produce CIO synthesis with veto context
        except Exception as e:
            logger.error(f"Veto evaluation failed: {e}")
            # Continue with caution flag
            result["phases"]["veto_error"] = str(e)

        # ═══════════════════════════════════════════════════════
        # FASE 4: Síntesis del CIO
        # ═══════════════════════════════════════════════════════
        try:
            cio = self.registry.get(AgentRole.CIO)
            if cio:
                cio_decision = await cio.synthesize_proposal(proposal)
                result["cio_synthesis"] = cio_decision
                self._log_phase(proposal.id, "CIO_SYNTHESIS", "Complete")
        except Exception as e:
            logger.error(f"CIO synthesis failed: {e}")
            result["phases"]["cio_error"] = str(e)

        # ═══════════════════════════════════════════════════════
        # FASE 5: Validación de completitud (Instrucción 5)
        # ═══════════════════════════════════════════════════════
        validation = self._validate_decision(result)
        result["validation"] = validation

        if validation["valid"] and not veto_check.get("blocked", False):
            proposal.status = DecisionStatus.AWAITING_USER
            result["status"] = DecisionStatus.AWAITING_USER
            result["ready_for_principal"] = True
        elif not veto_check.get("blocked", False):
            result["status"] = DecisionStatus.PENDING
            result["missing_requirements"] = validation.get("missing", [])

        proposal.updated_at = datetime.now(timezone.utc)
        self._log_phase(proposal.id, "PIPELINE_COMPLETE", f"Status: {result['status']}")

        return result

    def _validate_decision(self, result: dict[str, Any]) -> dict[str, Any]:
        """
        Instrucción 5: Valida que todas las condiciones se cumplen.
        """
        checks = {
            "analyzed_by_relevant_agents": (
                result.get("phases", {}).get("analysis", {}).get("count", 0) > 0
            ),
            "has_financial_impact": (
                result.get("committee_decision") is not None
            ),
            "has_fiscal_impact": (
                result.get("phases", {}).get("fiscal", {}).get("count", 0) > 0
            ),
            "evaluated_by_risk_manager": (
                "veto_check" in result
            ),
            "passed_investment_committee": (
                result.get("committee_decision") is not None
            ),
        }

        missing = [k for k, v in checks.items() if not v]

        return {
            "valid": all(checks.values()),
            "checks": checks,
            "missing": missing,
        }

    def _log_phase(self, proposal_id: str, phase: str, detail: str):
        entry = {
            "proposal_id": proposal_id,
            "phase": phase,
            "detail": detail,
            "timestamp": datetime.now(timezone.utc).isoformat(),
        }
        self._pipeline_log.append(entry)
        logger.info(f"[PIPELINE] {phase}: {detail}")

    def get_pipeline_log(self, proposal_id: str | None = None) -> list[dict]:
        if proposal_id:
            return [e for e in self._pipeline_log if e["proposal_id"] == proposal_id]
        return self._pipeline_log.copy()

    def format_principal_report(self, result: dict[str, Any]) -> str:
        """
        Formatea el resultado del pipeline para presentar al Principal.
        Instrucción 10: Opciones, trade-offs, advertencias.
        Instrucción 11: Ejecutivo, claro, estructurado.
        """
        proposal = result["proposal"]
        status = result["status"]

        lines = [
            "═" * 60,
            f"  FAMILY OFFICE — INFORME DE INVERSIÓN",
            "═" * 60,
            "",
            f"PROPUESTA: {proposal.title}",
            f"MONTO: USD {proposal.amount_usd:,.0f}",
            f"CLASE: {proposal.asset_class}",
            f"JURISDICCIÓN: {proposal.jurisdiction}",
            f"HORIZONTE: {proposal.time_horizon_months} meses",
            f"RETORNO BRUTO ESPERADO: {proposal.expected_gross_return_pct:.1f}%",
            "",
            f"ESTADO: {status.value.upper()}",
            "",
        ]

        # Analyses summary
        phases = result.get("phases", {})
        analysis_count = phases.get("analysis", {}).get("count", 0)
        fiscal_count = phases.get("fiscal", {}).get("count", 0)
        lines.append(f"ANÁLISIS COMPLETADOS: {analysis_count} financieros + {fiscal_count} fiscales")
        lines.append("")

        # Vetoes
        vetoes = result.get("vetoes", [])
        if vetoes:
            lines.append("⚠ VETOS ACTIVOS:")
            for v in vetoes:
                lines.append(f"  • [{v.agent_role.value}] {v.veto_type.value}: {v.justification}")
            lines.append("")
        else:
            lines.append("✓ Sin vetos activos")
            lines.append("")

        # CIO Synthesis
        cio = result.get("cio_synthesis")
        if cio:
            lines.append("SÍNTESIS DEL CIO:")
            lines.append(f"  {cio.cio_synthesis[:500]}")
            lines.append("")
            if cio.final_recommendation:
                lines.append(f"RECOMENDACIÓN: {cio.final_recommendation[:300]}")
                lines.append("")

        # Validation
        validation = result.get("validation", {})
        if validation.get("missing"):
            lines.append("⚠ REQUISITOS PENDIENTES:")
            for m in validation["missing"]:
                lines.append(f"  • {m}")
            lines.append("")

        # Principal action
        lines.append("─" * 60)
        if result.get("ready_for_principal"):
            lines.append("ACCIÓN REQUERIDA: Aprobar / Rechazar / Solicitar más análisis")
        elif status == DecisionStatus.VETOED:
            lines.append("ACCIÓN REQUERIDA: Resolver vetos o ejercer override (queda registrado)")
        else:
            lines.append("ACCIÓN REQUERIDA: Pendiente de completar análisis")
        lines.append("─" * 60)

        return "\n".join(lines)

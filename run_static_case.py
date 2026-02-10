#!/usr/bin/env python3
"""
Ejecución estática del pipeline del Family Office.
Inyecta respuestas realistas por agente (sin LLM ni APIs externas)
y ejecuta el pipeline completo de decisión.

Uso:
    python run_static_case.py
"""

from __future__ import annotations

import asyncio
import json
import sys
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import AsyncMock, patch

sys.path.insert(0, str(Path(__file__).parent))

from family_office.core.models import (
    AgentRole,
    DecisionStatus,
    InvestmentProposal,
)
from family_office.orchestrator import FamilyOfficeOrchestrator

# ═════════════════════════════════════════════════════════════════
# Respuestas estáticas por agente (simulan salida del LLM)
# ═════════════════════════════════════════════════════════════════

STATIC_RESPONSES: dict[str, str] = {}

# ── Capa 2: Análisis ──────────────────────────────────────────

STATIC_RESPONSES["macro_geopolitics"] = """\
HALLAZGOS CLAVE:
- Ciclo de tasas de la Fed en fase de pausa; el mercado descuenta 2 recortes en 2026
- GDP US creciendo al 2.1% anualizado, por encima de tendencia
- Riesgo geopolítico moderado: tensiones comerciales US-China contenidas
- Dólar estable (DXY 103-106), no hay presión de devaluación significativa
- Empleo robusto (unemployment 3.9%) soporta consumo y earnings corporativos

RIESGOS:
- Inflación persistente por encima del 2.5% podría retrasar recortes
- Escalada arancelaria US-China impactaría cadenas de suministro del S&P 500
- Elecciones US 2026 midterms: incertidumbre regulatoria sector tech

RECOMENDACIÓN:
Entorno macro favorable para equity US large cap. El ciclo económico está en expansión
tardía pero sin señales de recesión inminente. Convicción 0.72.
"""

STATIC_RESPONSES["fundamental"] = """\
HALLAZGOS CLAVE:
- S&P 500 cotiza a P/E forward de 21.3x, ligeramente por encima de la media histórica (19.5x)
- Earnings growth estimado para 2026: +9.2% YoY
- Margen neto agregado S&P 500: 12.1%, en máximos históricos
- Buybacks netos anualizados: USD 850B, soporte técnico para el índice
- Free cash flow yield del S&P 500: 4.2%, superior al Treasury 10Y real

RIESGOS:
- Valuación estirada vs. histórico; mean reversion implicaría -8% a -12%
- Concentración en Mag-7 (32% del índice), riesgo idiosincrático elevado
- Margen neto en máximos tiene poco upside y riesgo de compresión por salarios

RECOMENDACIÓN:
Fundamentales sólidos pero valuación exigente. Preferir entrada gradual (DCA 3 meses)
en lugar de lump sum. Considerar equal-weight para reducir concentración Mag-7. Convicción 0.65.
"""

STATIC_RESPONSES["technical_quant"] = """\
HALLAZGOS CLAVE:
- S&P 500 en tendencia alcista: precio sobre SMA 200 y SMA 50
- RSI(14) en 58, zona neutral-alcista, sin sobrecompra
- Volatilidad implícita (VIX) en 16.2, por debajo de media histórica (19.5)
- Momentum factor: +2.1% mensual, positivo y acelerando
- Breadth: 68% de componentes sobre SMA 200, saludable pero no extremo

RIESGOS:
- Soporte clave en 5,150 (SMA 200); ruptura implicaría corrección del -7% a -10%
- Put/call ratio en 0.72, optimismo moderado, sin señal contrarian
- Estacionalidad: H2 2026 históricamente más débil que H1

RECOMENDACIÓN:
Señales técnicas alineadas al alza. Entry point razonable con stop-loss en SMA 200 (-4.8%).
Target 12 meses: +11.5% basado en momentum y extensión de tendencia. Convicción 0.70.
"""

STATIC_RESPONSES["credit_bonds"] = """\
HALLAZGOS CLAVE:
- Treasury 10Y en 4.15%, curva de rendimiento normalizada (pendiente +25bp)
- Investment grade spreads: 95bp, en percentil 25 histórico (apretados)
- High yield spreads: 320bp, sin estrés crediticio significativo
- Default rate trailing 12m: 1.8%, por debajo de media (2.5%)
- Equity risk premium (ERP): 4.9%, favorece equities sobre bonos

RIESGOS:
- Spreads comprimidos dejan poco margen para compresión adicional
- Refinanciamiento corporativo 2026-2027: USD 1.2T en IG y HY combinado
- Si la Fed no recorta, renta fija compite más agresivamente con equity

RECOMENDACIÓN:
El ERP favorece equity sobre bonos en horizonte 12 meses. Sin embargo, la posición
debería complementarse con un 15-20% en Treasuries como hedge de recesión. Convicción 0.60.
"""

STATIC_RESPONSES["real_assets"] = """\
HALLAZGOS CLAVE:
- REITs US cotizan a descuento del 12% vs. NAV, atractivos vs. equity
- Oro en USD 2,340/oz, rango lateral. Sin catalizador claro a corto plazo
- Petróleo WTI en USD 78, OPEC+ manteniendo recortes
- Infraestructura: yields del 5.2-5.8%, atractivos vs. equity dividend yield (1.5%)
- Commodities agrícolas: precios normalizados post-shock 2022-2023

RIESGOS:
- REITs sensibles a tasas; si la Fed no recorta, underperformance continúa
- Oro no genera cash flow; costo de oportunidad alto en entorno de tasas >4%

RECOMENDACIÓN:
Para una posición de USD 500K en equity US, no es necesaria exposición directa a real assets.
Si el Principal busca diversificación, considerar 5-10% en REITs como complemento. Convicción 0.55.
"""

# ── Capa 3: Fiscal ────────────────────────────────────────────

STATIC_RESPONSES["fiscal_spain"] = """\
HALLAZGOS CLAVE:
- Residencia fiscal: España. Tributación mundial (renta mundial del IRPF)
- Dividendos US: retención en origen 15% (CDI US-ES) + IRPF 19-28%
- Ganancias de capital: IRPF al 19% (primeros EUR 6K), 21% (6K-50K), 23% (50K-200K), 28% (>200K)
- Impuesto sobre el Patrimonio: aplicable si base >EUR 3.7M (según CCAA)
- Modelo 720: obligación de declarar activos en el extranjero >EUR 50K

RIESGOS:
- Si inversión via sociedad interpuesta, riesgo de CFC (Art. 100 LIS)
- Modelo 720: sanción desproporcionada por no declarar (pendiente reforma)
- Cambio normativo: posible incremento del tipo de ahorro en 2027

RECOMENDACIÓN:
Inversión directa en brokerage a nombre personal. Evitar estructuras interpuestas
para USD 500K (no justifica complejidad). Tax drag estimado: 23.5% efectivo sobre retornos.
"""

STATIC_RESPONSES["fiscal_portugal"] = """\
HALLAZGOS CLAVE:
- Sin impacto directo si el Principal es residente fiscal en España
- NHR ya expirado para nuevas solicitudes
- CDI Portugal-US no aplica (Principal no es residente PT)
- Si hay activos inmobiliarios en PT, tributación separada

RIESGOS:
- Ninguno relevante para esta operación

RECOMENDACIÓN:
Sin impacto fiscal desde Portugal para esta inversión. No requiere acción.
"""

STATIC_RESPONSES["fiscal_panama"] = """\
HALLAZGOS CLAVE:
- Panamá: sistema territorial, no grava rentas de fuente extranjera
- Si existe sociedad panameña (SEM/SA), los dividendos US serían exentos en PA
- Sin embargo, desde España se aplicaría CFC si la sociedad es instrumental

RIESGOS:
- CFC español imputaría la renta al residente en España
- Sustancia mínima requerida: oficina, empleados, decisiones locales

RECOMENDACIÓN:
No usar vehículo panameño para esta inversión. El beneficio fiscal queda anulado
por normativa CFC española y el costo de sustancia no se justifica para USD 500K.
"""

STATIC_RESPONSES["fiscal_barbados"] = """\
HALLAZGOS CLAVE:
- IBC Barbados: tasa efectiva 1-2.5% sobre beneficios
- CDI Barbados-España no existe; sin protección contra doble imposición
- Sin CDI, España aplicaría régimen de transparencia fiscal (CFC)

RIESGOS:
- Alto riesgo CFC desde España
- Barbados en proceso de revisión OCDE (sustancia)
- Sin CDI España-Barbados, retención plena sobre dividendos

RECOMENDACIÓN:
Descartado como jurisdicción para esta operación. Sin CDI con España y alto riesgo CFC.
"""

STATIC_RESPONSES["fiscal_us"] = """\
HALLAZGOS CLAVE:
- Retención en origen US sobre dividendos: 30% (sin CDI) o 15% (con CDI ES-US)
- CDI España-US activo; permite reducción al 15% en dividendos
- Ganancias de capital: no sujetas a retención US para non-resident aliens (NRA)
- FATCA: reporte automático al IRS de cuentas >USD 50K
- Estate tax US: aplica a NRA con activos US situs >USD 60K (riesgo si fallecimiento)

RIESGOS:
- Estate tax US: tasa del 40% sobre activos US situs para NRA (mitigable con estructura)
- FATCA reporting obligatorio; cumplimiento automático via broker regulado

RECOMENDACIÓN:
Inversión directa viable. Retención 15% sobre dividendos (recuperable parcialmente en IRPF).
ALERTA: estate tax exposure para USD 500K. Considerar seguro de vida o treaty planning.
Tax drag US: 15% sobre dividend yield (~1.5% del S&P = ~USD 1,125/año).
"""

STATIC_RESPONSES["fiscal_venezuela"] = """\
HALLAZGOS CLAVE:
- ISLR Venezuela: aplica a residentes fiscales sobre renta mundial
- Si el Principal NO es residente fiscal VE, sin impacto directo
- Control cambiario: no aplica para inversiones offshore de no-residentes
- Sanciones OFAC: no aplican a inversión en S&P 500 (activo US, no VE)

RIESGOS:
- Si el Principal mantiene residencia fiscal dual (ES+VE), doble tributación
- Verificar estatus de residencia fiscal VE formalmente

RECOMENDACIÓN:
Sin impacto fiscal desde Venezuela para residente fiscal español.
Confirmar que no existe residencia fiscal dual vigente.
"""

STATIC_RESPONSES["cross_border"] = """\
HALLAZGOS CLAVE:
- Flujo principal: US (fuente) → España (residencia). CDI activo.
- Dividendos: retención 15% US + tributación IRPF 19-28% ES con crédito fiscal
- Capital gains: exentos en US para NRA, gravados en España al 19-28%
- Transfer pricing: no aplica (inversión directa, sin entidades intermedias)
- DAC6: no hay esquema reportable (inversión directa en mercado regulado)

RIESGOS:
- Cambio de CDI US-ES: probabilidad baja pero monitoreada
- PE risk: inexistente para inversión pasiva en ETF/acciones

RECOMENDACIÓN:
Estructura limpia: inversión directa US → tributación en España con crédito fiscal.
Retorno neto post-impuestos estimado: 7.2% (sobre 10% bruto esperado).
Sin riesgos CFC, PE o substance. Estructura defendible al 100%.
"""

# ── Dirección ─────────────────────────────────────────────────

STATIC_RESPONSES["investment_committee"] = """\
ACUERDOS ENTRE AGENTES:
- Consenso: entorno macro favorable para equity US en horizonte 12 meses
- Consenso: fundamentales sólidos, earnings growth positivo
- Consenso: señales técnicas alineadas al alza
- Consenso: estructura fiscal directa US→ES es la más eficiente para este monto
- Consenso: no usar vehículos interpuestos (Panamá, Barbados) por riesgo CFC

CONTRADICCIONES:
- Fundamental vs. Técnico: valuación estirada (P/E 21.3x) vs. momentum positivo
- Crédito sugiere complementar con 15-20% Treasuries; Fundamental prefiere 100% equity
- Real Assets sugiere 5-10% REITs como diversificación; no respaldado por otros agentes

ESCENARIO BASE:
Retorno bruto +10% en 12 meses. S&P 500 alcanza 5,900-6,100. Earnings crecen 9%.
Tax drag efectivo: 23.5% sobre ganancias. Retorno neto post-tax: ~7.2%.

ESCENARIO OPTIMISTA:
Fed recorta 2 veces, múltiplo expande a 23x, retorno bruto +16%. Neto: ~12.2%.

ESCENARIO ADVERSO:
Inflación persistente, Fed mantiene tasas, múltiplo comprime a 18x. Retorno: -8% a -12%.
Protección: stop-loss en SMA 200 limita drawdown al -5%.

RIESGOS PRINCIPALES:
- Valuación estirada: P/E forward 21.3x vs. media 19.5x
- Concentración Mag-7: 32% del índice
- Estate tax US: 40% sobre USD 500K si fallecimiento del Principal
- Inflación persistente retrasando recortes de la Fed

SÍNTESIS PARA EL CIO:
Propuesta con fundamento sólido. Risk/reward favorable en horizonte 12m.
Principales mitigantes: entrada gradual (DCA 3 meses), equal-weight ETF opcional,
y planificación para estate tax US.

CONDICIONES DE INVALIDACIÓN:
- Recesión US confirmada (2 trimestres consecutivos GDP negativo)
- VIX sostenido sobre 30 por más de 2 semanas
- Ruptura del S&P 500 por debajo de SMA 200 con volumen
- Cambio en CDI US-ES que elimine crédito fiscal
"""

STATIC_RESPONSES["cio"] = """\
SÍNTESIS DEL CIO — INVERSIÓN EN EQUITY US LARGE CAP

ESCENARIO BASE:
Inversión de USD 500,000 en equity US large cap (S&P 500 / equal-weight ETF).
Retorno bruto esperado: +10% (USD 50,000) en 12 meses.
Tax drag: ~23.5% efectivo (retención US 15% + IRPF diferencial).
Retorno neto post-impuestos: ~7.2% (USD 36,000).

ESCENARIO OPTIMISTA:
Si la Fed recorta 2 veces y earnings superan estimaciones: +16% bruto, ~12.2% neto.

ESCENARIO ADVERSO:
Inflación persistente + compresión de múltiplos: -8% a -12%. Stop-loss en SMA 200
limita drawdown al -5% (-USD 25,000).

RIESGOS PRINCIPALES:
- Valuación P/E 21.3x por encima de media histórica 19.5x
- Concentración Mag-7 en cap-weighted index
- Estate tax US exposure (40% sobre USD 500K)
- Riesgo macro: inflación > 2.5% retrasa recortes Fed

DECISIÓN RECOMENDADA:
APROBACIÓN CON CONDICIONES:
1. Entrada gradual via DCA en 3 tranches mensuales de USD 166,666
2. Considerar RSP (equal-weight S&P 500 ETF) vs. SPY para mitigar Mag-7
3. Implementar stop-loss a nivel portfolio en SMA 200 del S&P
4. Iniciar planning de estate tax US (seguro de vida o treaty review)
5. Próxima revisión: a los 6 meses o si VIX > 25

CONDICIONES DE INVALIDACIÓN:
- Recesión US confirmada (2Q GDP negativo)
- VIX sostenido sobre 30 por 2+ semanas
- Ruptura confirmada bajo SMA 200 con volumen elevado
- Modificación del CDI US-ES

RETORNO NETO POST-IMPUESTOS: 7.2% estimado (base case).
"""

# ── Riesgo y Tax veto ─────────────────────────────────────────

STATIC_RESPONSES["risk_manager"] = """\
EVALUACIÓN DE RIESGO — EQUITY US LARGE CAP USD 500K

HALLAZGOS CLAVE:
- Posición representaría ~X% del portfolio (depende del tamaño total)
- Correlación con posiciones existentes: pendiente de evaluar
- VaR 95% 1-día estimado: USD 15,800 (3.16% — basado en vol histórica 20%)
- CVaR 95%: USD 22,500 (tail risk)
- Max drawdown histórico S&P 500 12m: -33.9% (COVID), -38.5% (2008)
- Liquidez: excelente (S&P 500 ETF, bid-ask <1bp)

RIESGOS IDENTIFICADOS:
- Drawdown máximo esperado en escenario adverso: USD 60,000-75,000 (-12% a -15%)
- Sin cobertura (hedge), drawdown podría exceder límite del 15% del portfolio

RECOMENDACIÓN:
NO EMITIR VETO. La posición tiene liquidez excelente y el drawdown esperado
está dentro de límites aceptables con stop-loss en SMA 200.
Condiciones: implementar stop-loss y revisar sizing si portfolio total < USD 2.5M.
"""

STATIC_RESPONSES["head_tax_strategy"] = """\
NO_VETO — Estructura directa US→España fiscalmente limpia.
CDI activo, sin riesgo CFC, sin entidades interpuestas.
Tax drag aceptable (23.5% efectivo). Estructura defendible ante AEAT.
"""

STATIC_RESPONSES["tax_risk_audit"] = """\
HALLAZGOS CLAVE:
- Riesgo de auditoría: BAJO para inversión directa en mercado regulado US
- Modelo 720: cumplimiento requerido (activos >EUR 50K en extranjero)
- FATCA: reporte automático — cumplimiento via broker US regulado
- No hay esquema DAC6 reportable
- Estructura no tiene agresividad fiscal

RIESGOS:
- Olvido de Modelo 720: sanción proporcional (ya no desproporcionada post-reforma)

RECOMENDACIÓN:
Riesgo de auditoría mínimo. Asegurar cumplimiento de Modelo 720 y declaración
de ganancias/dividendos en IRPF. Sin estructura agresiva que atraiga inspección.
"""


def _get_agent_role_from_prompt(system_prompt: str, user_prompt: str) -> str:
    """Identifica el agente a partir del campo 'Rol:' del system prompt."""
    import re

    # Extraer el campo "Rol: <role_value>" del system prompt (único por agente)
    match = re.search(r"Rol:\s*(\w+)", system_prompt)
    if match:
        role = match.group(1)
        if role in STATIC_RESPONSES:
            return role

    # Fallback por nombre del agente
    sp = system_prompt.lower()
    up = user_prompt.lower()

    # Orden preciso: nombres completos primero para evitar collision
    role_map = [
        ("rol: risk_manager", "risk_manager"),
        ("rol: head_tax_strategy", "head_tax_strategy"),
        ("rol: cio", "cio"),
        ("rol: investment_committee", "investment_committee"),
        ("rol: macro_geopolitics", "macro_geopolitics"),
        ("rol: fundamental", "fundamental"),
        ("rol: technical_quant", "technical_quant"),
        ("rol: credit_bonds", "credit_bonds"),
        ("rol: real_assets", "real_assets"),
        ("rol: fiscal_spain", "fiscal_spain"),
        ("rol: fiscal_portugal", "fiscal_portugal"),
        ("rol: fiscal_panama", "fiscal_panama"),
        ("rol: fiscal_barbados", "fiscal_barbados"),
        ("rol: fiscal_us", "fiscal_us"),
        ("rol: fiscal_venezuela", "fiscal_venezuela"),
        ("rol: cross_border", "cross_border"),
        ("rol: tax_risk_audit", "tax_risk_audit"),
        ("rol: opportunity_scanner", "opportunity_scanner"),
        ("rol: portfolio_ops", "portfolio_ops"),
    ]

    for keyword, role in role_map:
        if keyword in sp:
            return role

    # Fallback: check user prompt for veto evaluation
    if "veto" in up and "fiscal" in up:
        return "head_tax_strategy"

    return "unknown"


async def mock_call_llm(system_prompt: str, user_prompt: str, **kwargs) -> str:
    """Reemplaza call_llm con respuestas estáticas realistas."""
    role = _get_agent_role_from_prompt(system_prompt, user_prompt)
    response = STATIC_RESPONSES.get(role)
    if response:
        return response
    return f"[STATIC — {role}] Análisis no disponible en modo estático."


def serialize_result(result: dict) -> dict:
    """Serializa el resultado del pipeline a JSON-safe dict."""
    output = {}

    # Proposal
    proposal = result["proposal"]
    output["proposal"] = {
        "id": proposal.id,
        "title": proposal.title,
        "asset_class": proposal.asset_class,
        "description": proposal.description,
        "amount_usd": proposal.amount_usd,
        "expected_gross_return_pct": proposal.expected_gross_return_pct,
        "time_horizon_months": proposal.time_horizon_months,
        "jurisdiction": proposal.jurisdiction,
        "status": proposal.status.value,
        "created_at": proposal.created_at.isoformat(),
        "updated_at": proposal.updated_at.isoformat(),
    }

    # Analyses
    output["analyses"] = []
    for a in proposal.analyses:
        output["analyses"].append({
            "agent_role": a.agent_role.value,
            "subject": a.subject,
            "summary": a.summary[:300] + "..." if len(a.summary) > 300 else a.summary,
            "conviction_level": a.conviction_level,
            "key_findings": a.key_findings,
            "risks_identified": a.risks_identified,
            "recommendation": a.recommendation,
            "timestamp": a.timestamp.isoformat(),
        })

    # Phases
    output["phases"] = result.get("phases", {})

    # Vetoes
    output["vetoes"] = []
    for v in result.get("vetoes", []):
        output["vetoes"].append({
            "agent_role": v.agent_role.value,
            "veto_type": v.veto_type.value,
            "justification": v.justification,
            "severity": v.severity,
            "conditions_to_lift": v.conditions_to_lift,
            "timestamp": v.timestamp.isoformat(),
        })

    # Veto check
    veto_check = result.get("veto_check", {})
    output["veto_check"] = {
        "blocked": veto_check.get("blocked", False),
        "status": veto_check.get("status", DecisionStatus.PENDING).value
            if hasattr(veto_check.get("status", ""), "value")
            else str(veto_check.get("status", "")),
        "veto_summary": veto_check.get("veto_summary", ""),
        "can_override": veto_check.get("can_override", True),
    }

    # Committee Decision
    cd = result.get("committee_decision")
    if cd:
        output["committee_decision"] = {
            "id": cd.id,
            "proposal_id": cd.proposal_id,
            "agreements": cd.agreements,
            "contradictions": cd.contradictions,
            "status": cd.status.value,
            "requires_user_approval": cd.requires_user_approval,
            "timestamp": cd.timestamp.isoformat(),
        }
        if cd.scenarios:
            output["committee_decision"]["scenarios"] = {
                "scenario_base": cd.scenarios.scenario_base,
                "scenario_optimistic": cd.scenarios.scenario_optimistic,
                "scenario_adverse": cd.scenarios.scenario_adverse,
                "main_risks": cd.scenarios.main_risks,
                "recommended_decision": cd.scenarios.recommended_decision,
                "invalidation_conditions": cd.scenarios.invalidation_conditions,
            }

    # CIO Synthesis
    cio = result.get("cio_synthesis")
    if cio:
        output["cio_synthesis"] = {
            "id": cio.id,
            "proposal_id": cio.proposal_id,
            "cio_synthesis": cio.cio_synthesis,
            "final_recommendation": cio.final_recommendation,
            "status": cio.status.value,
        }
        if cio.scenarios:
            output["cio_synthesis"]["scenarios"] = {
                "scenario_base": cio.scenarios.scenario_base,
                "scenario_optimistic": cio.scenarios.scenario_optimistic,
                "scenario_adverse": cio.scenarios.scenario_adverse,
                "main_risks": cio.scenarios.main_risks,
                "recommended_decision": cio.scenarios.recommended_decision,
                "invalidation_conditions": cio.scenarios.invalidation_conditions,
            }

    # Validation
    output["validation"] = result.get("validation", {})

    # Final status
    status = result.get("status", DecisionStatus.PENDING)
    output["status"] = status.value if hasattr(status, "value") else str(status)
    output["ready_for_principal"] = result.get("ready_for_principal", False)

    # Pattern alerts
    output["pattern_alerts"] = result.get("pattern_alerts", [])

    return output


async def main():
    print("=" * 70)
    print("  FAMILY OFFICE — EJECUCIÓN ESTÁTICA DEL PIPELINE")
    print("  Caso: Equity US Large Cap — USD 500,000 — 12 meses")
    print("=" * 70)
    print()

    # Patch call_llm en los módulos que lo importan por nombre
    import family_office.core.base_agent as _base_agent_mod
    import family_office.core.llm_client as _llm_client_mod

    _original_base = _base_agent_mod.call_llm
    _original_llm = _llm_client_mod.call_llm

    _base_agent_mod.call_llm = mock_call_llm
    _llm_client_mod.call_llm = mock_call_llm

    try:
        # Inicializar sistema
        print("[1/6] Inicializando organización (20 agentes, 5 capas)...")
        orchestrator = FamilyOfficeOrchestrator()
        orchestrator.initialize()
        print(f"       {orchestrator.registry.agent_count} agentes registrados.\n")

        # Crear propuesta
        print("[2/6] Creando propuesta de inversión...")
        proposal = InvestmentProposal(
            title="S&P 500 Large Cap Equity — DCA Entry",
            asset_class="Renta Variable",
            description=(
                "Inversión en equity US large cap via ETF (SPY/RSP). "
                "Entrada gradual en 3 tranches mensuales. "
                "Horizonte 12 meses con revisión semestral."
            ),
            amount_usd=500_000.0,
            expected_gross_return_pct=10.0,
            time_horizon_months=12,
            jurisdiction="Estados Unidos",
        )
        print(f"       ID: {proposal.id}")
        print(f"       Título: {proposal.title}")
        print(f"       Monto: USD {proposal.amount_usd:,.0f}")
        print(f"       Retorno bruto esperado: {proposal.expected_gross_return_pct}%\n")

        # Ejecutar pipeline
        print("[3/6] Fase 1+2: Análisis independiente (5 agentes) + Fiscal (7 agentes)...")
        print("       → Los agentes NO ven el trabajo de los otros.")
        print("[4/6] Fase 3: Debate del Comité de Inversión...")
        print("[5/6] Fase 4: Veto Gate (Risk Manager + Head of Tax)...")
        print("[6/6] Fase 5-7: Síntesis CIO + Validación + Presentación...")
        print()

        result = await orchestrator.process_proposal(proposal)

        # ═══════════════════════════════════════════════════════════
        # Mostrar DecisionRecord completo
        # ═══════════════════════════════════════════════════════════

        decision_record = serialize_result(result)

        print("=" * 70)
        print("  DECISION RECORD COMPLETO (JSON)")
        print("=" * 70)
        print(json.dumps(decision_record, indent=2, ensure_ascii=False, default=str))

        # ═══════════════════════════════════════════════════════════
        # Reporte formateado para el Principal
        # ═══════════════════════════════════════════════════════════

        print()
        print()
        report = orchestrator.pipeline.format_principal_report(result)
        print(report)

        # ═══════════════════════════════════════════════════════════
        # Pipeline log
        # ═══════════════════════════════════════════════════════════

        print()
        print("=" * 70)
        print("  PIPELINE LOG")
        print("=" * 70)
        for entry in orchestrator.pipeline.get_pipeline_log():
            print(f"  [{entry['phase']}] {entry['detail']}  — {entry['timestamp']}")

        # ═══════════════════════════════════════════════════════════
        # Decision store
        # ═══════════════════════════════════════════════════════════

        print()
        print("=" * 70)
        print("  DECISION STORE (persistido en disco)")
        print("=" * 70)
        stored = orchestrator.decision_store.get_decision(proposal.id)
        if stored:
            print(json.dumps(stored, indent=2, ensure_ascii=False, default=str))
        else:
            print("  (no persistido)")

    finally:
        _base_agent_mod.call_llm = _original_base
        _llm_client_mod.call_llm = _original_llm


if __name__ == "__main__":
    asyncio.run(main())

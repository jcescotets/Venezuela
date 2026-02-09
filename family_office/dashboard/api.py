"""
Dashboard API — FastAPI backend para el Family Office Dashboard.
Endpoints para portfolio, análisis, decisiones y datos de mercado.
"""

from __future__ import annotations

import logging
from typing import Any

from fastapi import FastAPI, HTTPException, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

logger = logging.getLogger(__name__)

# Templates & static files
DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"

app = FastAPI(
    title="Family Office Dashboard",
    description="Panel de control del Family Office Agéntico",
    version="1.0.0",
)

if STATIC_DIR.exists():
    app.mount("/static", StaticFiles(directory=str(STATIC_DIR)), name="static")

templates = Jinja2Templates(directory=str(TEMPLATES_DIR))

# These will be injected by the orchestrator at startup
_orchestrator = None
_market_service = None
_macro_service = None
_decision_store = None
_memory_manager = None


def set_services(orchestrator, market_svc, macro_svc, decision_store, memory_mgr):
    global _orchestrator, _market_service, _macro_service, _decision_store, _memory_manager
    _orchestrator = orchestrator
    _market_service = market_svc
    _macro_service = macro_svc
    _decision_store = decision_store
    _memory_manager = memory_mgr


# ═══════════════════════════════════════════════════════
# HTML Pages
# ═══════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ═══════════════════════════════════════════════════════
# API: Organization
# ═══════════════════════════════════════════════════════

@app.get("/api/organization")
async def get_organization():
    """Retorna la estructura organizativa del Family Office."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")
    return {
        "summary": _orchestrator.registry.summary(),
        "agent_count": _orchestrator.registry.agent_count,
        "agents": [
            {
                "name": a.name,
                "role": a.role.value,
                "layer": a.layer.value,
                "specialty": a.contract.specialty,
                "has_veto": bool(a.contract.can_veto),
            }
            for a in _orchestrator.registry.all_agents()
        ],
    }


# ═══════════════════════════════════════════════════════
# API: Portfolio
# ═══════════════════════════════════════════════════════

@app.get("/api/portfolio")
async def get_portfolio():
    """Retorna el estado actual del portfolio."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")
    from family_office.core.models import AgentRole
    port_ops = _orchestrator.registry.get(AgentRole.PORTFOLIO_OPS)
    if port_ops:
        snapshot = port_ops.get_snapshot()
        return snapshot.model_dump(mode="json")
    return {"assets": [], "total_value_usd": 0}


class AssetInput(BaseModel):
    name: str
    ticker: str | None = None
    asset_class: str
    jurisdiction: str
    holding_vehicle: str | None = None
    quantity: float
    cost_basis_usd: float
    current_value_usd: float
    currency: str = "USD"
    notes: str = ""


@app.post("/api/portfolio/asset")
async def add_portfolio_asset(asset: AssetInput):
    """Agrega un activo al portfolio."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")
    from family_office.core.models import AgentRole, PortfolioAsset
    port_ops = _orchestrator.registry.get(AgentRole.PORTFOLIO_OPS)
    if port_ops:
        pa = PortfolioAsset(**asset.model_dump())
        port_ops.add_asset(pa)
        return {"status": "added", "asset_id": pa.id}
    raise HTTPException(500, "Portfolio Operations agent not available")


# ═══════════════════════════════════════════════════════
# API: Market Data
# ═══════════════════════════════════════════════════════

@app.get("/api/market/stock/{ticker}")
async def get_stock(ticker: str):
    if _market_service is None:
        raise HTTPException(503, "Market service not initialized")
    return await _market_service.get_stock_data(ticker)


@app.get("/api/market/macro")
async def get_macro_dashboard():
    if _macro_service is None:
        raise HTTPException(503, "Macro service not initialized")
    return await _macro_service.get_macro_dashboard()


@app.get("/api/market/forex/{from_curr}/{to_curr}")
async def get_forex(from_curr: str, to_curr: str):
    if _market_service is None:
        raise HTTPException(503, "Market service not initialized")
    return await _market_service.get_forex_rate(from_curr.upper(), to_curr.upper())


# ═══════════════════════════════════════════════════════
# API: Decisions
# ═══════════════════════════════════════════════════════

@app.get("/api/decisions")
async def list_decisions(status: str | None = None):
    if _decision_store is None:
        raise HTTPException(503, "Decision store not initialized")
    return _decision_store.get_all_decisions(status)


@app.get("/api/decisions/{decision_id}")
async def get_decision(decision_id: str):
    if _decision_store is None:
        raise HTTPException(503, "Decision store not initialized")
    result = _decision_store.get_decision(decision_id)
    if result is None:
        raise HTTPException(404, "Decision not found")
    return result


# ═══════════════════════════════════════════════════════
# API: Analysis (trigger new analysis)
# ═══════════════════════════════════════════════════════

class AnalysisRequest(BaseModel):
    title: str
    asset_class: str
    description: str
    amount_usd: float
    expected_gross_return_pct: float
    time_horizon_months: int = 12
    jurisdiction: str = "global"
    holding_vehicle: str | None = None


@app.post("/api/analyze")
async def trigger_analysis(req: AnalysisRequest):
    """Lanza un análisis completo a través del pipeline."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")

    from family_office.core.models import InvestmentProposal
    proposal = InvestmentProposal(
        title=req.title,
        asset_class=req.asset_class,
        description=req.description,
        amount_usd=req.amount_usd,
        expected_gross_return_pct=req.expected_gross_return_pct,
        time_horizon_months=req.time_horizon_months,
        jurisdiction=req.jurisdiction,
        holding_vehicle=req.holding_vehicle,
    )

    result = await _orchestrator.process_proposal(proposal)
    return {
        "proposal_id": proposal.id,
        "status": result["status"].value,
        "ready_for_principal": result["ready_for_principal"],
        "report": _orchestrator.pipeline.format_principal_report(result),
    }


# ═══════════════════════════════════════════════════════
# API: Memory & Criteria
# ═══════════════════════════════════════════════════════

@app.get("/api/criteria")
async def get_criteria():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_criteria()


@app.get("/api/alerts")
async def get_alerts():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_alerts()


@app.get("/api/preferences")
async def get_preferences():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_preferences()

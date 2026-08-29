"""
Dashboard API — FastAPI backend para el Family Office Dashboard.
Endpoints para portfolio, análisis, decisiones, datos de mercado,
WebSocket para progreso en tiempo real, y gestión de memoria.
"""

from __future__ import annotations

import json
import logging
from datetime import datetime, timezone
from typing import Any

from fastapi import FastAPI, HTTPException, Request, WebSocket, WebSocketDisconnect
from fastapi.responses import HTMLResponse, Response
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from pathlib import Path
from pydantic import BaseModel

from family_office.pipeline.pipeline_events import pipeline_events

logger = logging.getLogger(__name__)

# Templates & static files
DASHBOARD_DIR = Path(__file__).parent
TEMPLATES_DIR = DASHBOARD_DIR / "templates"
STATIC_DIR = DASHBOARD_DIR / "static"

app = FastAPI(
    title="Family Office Dashboard",
    description="Panel de control del Family Office Agéntico",
    version="2.0.0",
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
# WebSocket Connection Manager
# ═══════════════════════════════════════════════════════

class ConnectionManager:
    """Manages WebSocket connections for real-time updates."""

    def __init__(self):
        self.active_connections: list[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"WebSocket client connected. Total: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        self.active_connections = [c for c in self.active_connections if c is not websocket]
        logger.info(f"WebSocket client disconnected. Total: {len(self.active_connections)}")

    async def broadcast(self, data: dict[str, Any]):
        dead = []
        for connection in self.active_connections:
            try:
                await connection.send_json(data)
            except Exception:
                dead.append(connection)
        for d in dead:
            self.disconnect(d)


ws_manager = ConnectionManager()


async def _pipeline_event_handler(event: dict[str, Any]):
    """Forward pipeline events to all WebSocket clients."""
    await ws_manager.broadcast(event)


# Register the handler on startup
pipeline_events.subscribe(_pipeline_event_handler)


# ═══════════════════════════════════════════════════════
# HTML Pages
# ═══════════════════════════════════════════════════════

@app.get("/", response_class=HTMLResponse)
async def dashboard_home(request: Request):
    return templates.TemplateResponse("dashboard.html", {"request": request})


# ═══════════════════════════════════════════════════════
# WebSocket Endpoint
# ═══════════════════════════════════════════════════════

@app.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await ws_manager.connect(websocket)
    try:
        while True:
            data = await websocket.receive_text()
            msg = json.loads(data) if data else {}
            if msg.get("type") == "ping":
                await websocket.send_json({"type": "pong"})
    except WebSocketDisconnect:
        ws_manager.disconnect(websocket)
    except Exception:
        ws_manager.disconnect(websocket)


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
                "primary_objective": a.contract.primary_objective,
                "reports_to": [r.value for r in a.contract.reports_to],
                "interacts_with": [r.value for r in a.contract.interacts_with],
            }
            for a in _orchestrator.registry.all_agents()
        ],
    }


@app.get("/api/organization/agent/{role}")
async def get_agent_detail(role: str):
    """Retorna detalles de un agente específico."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")
    from family_office.core.models import AgentRole
    try:
        agent_role = AgentRole(role)
    except ValueError:
        raise HTTPException(404, f"Agent role '{role}' not found")

    agent = _orchestrator.registry.get(agent_role)
    if agent is None:
        raise HTTPException(404, f"Agent '{role}' not registered")

    c = agent.contract
    return {
        "name": c.name,
        "role": c.role.value,
        "layer": c.layer.value,
        "specialty": c.specialty,
        "primary_objective": c.primary_objective,
        "can_recommend": c.can_recommend,
        "can_veto": c.can_veto,
        "inputs": c.inputs,
        "outputs": c.outputs,
        "reports_to": [r.value for r in c.reports_to],
        "interacts_with": [r.value for r in c.interacts_with],
        "restrictions": c.restrictions,
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
        await ws_manager.broadcast({
            "type": "portfolio_update",
            "action": "asset_added",
            "asset": asset.model_dump(),
        })
        return {"status": "added", "asset_id": pa.id}
    raise HTTPException(500, "Portfolio Operations agent not available")


@app.delete("/api/portfolio/asset/{asset_id}")
async def remove_portfolio_asset(asset_id: str):
    """Elimina un activo del portfolio."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")
    from family_office.core.models import AgentRole
    port_ops = _orchestrator.registry.get(AgentRole.PORTFOLIO_OPS)
    if port_ops:
        port_ops.remove_asset(asset_id)
        await ws_manager.broadcast({
            "type": "portfolio_update",
            "action": "asset_removed",
            "asset_id": asset_id,
        })
        return {"status": "removed", "asset_id": asset_id}
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


@app.get("/api/market/calendar")
async def get_economic_calendar():
    if _macro_service is None:
        raise HTTPException(503, "Macro service not initialized")
    return await _macro_service.get_economic_calendar()


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


class OutcomeInput(BaseModel):
    outcome: str
    actual_return_pct: float | None = None
    lessons: list[str] = []


@app.post("/api/decisions/{decision_id}/outcome")
async def record_outcome(decision_id: str, outcome: OutcomeInput):
    """Registra el resultado real de una decisión."""
    if _decision_store is None:
        raise HTTPException(503, "Decision store not initialized")
    _decision_store.store_outcome(
        decision_id,
        outcome.outcome,
        outcome.actual_return_pct,
        outcome.lessons,
    )
    return {"status": "recorded", "decision_id": decision_id}


@app.get("/api/decisions/patterns/mistakes")
async def get_past_mistakes():
    """Obtiene decisiones pasadas con resultados negativos."""
    if _decision_store is None:
        raise HTTPException(503, "Decision store not initialized")
    return _decision_store.get_past_mistakes()


# ═══════════════════════════════════════════════════════
# API: Pipeline
# ═══════════════════════════════════════════════════════

@app.get("/api/pipeline/log")
async def get_pipeline_log(proposal_id: str | None = None):
    """Retorna el log de fases del pipeline."""
    if _orchestrator is None or _orchestrator.pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    return _orchestrator.pipeline.get_pipeline_log(proposal_id)


@app.get("/api/pipeline/events")
async def get_pipeline_events(proposal_id: str | None = None):
    """Retorna los eventos en tiempo real del pipeline."""
    return pipeline_events.get_event_log(proposal_id)


@app.get("/api/pipeline/veto-history")
async def get_veto_history():
    """Retorna el historial completo de vetos."""
    if _orchestrator is None or _orchestrator.pipeline is None:
        raise HTTPException(503, "Pipeline not initialized")
    vetoes = _orchestrator.pipeline.veto_gate.veto_history
    return [v.model_dump(mode="json") for v in vetoes]


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


class QuickAnalysisRequest(BaseModel):
    subject: str
    agent_role: str
    context: dict[str, Any] = {}


@app.post("/api/analyze/quick")
async def trigger_quick_analysis(req: QuickAnalysisRequest):
    """Solicita análisis rápido a un agente específico."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")

    from family_office.core.models import AgentRole
    try:
        role = AgentRole(req.agent_role)
    except ValueError:
        raise HTTPException(400, f"Invalid agent role: {req.agent_role}")

    result = await _orchestrator.quick_analysis(req.subject, role, req.context)
    return result


# ═══════════════════════════════════════════════════════
# API: Memory & Criteria
# ═══════════════════════════════════════════════════════

@app.get("/api/criteria")
async def get_criteria():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_criteria()


class CriteriaUpdate(BaseModel):
    key: str
    value: Any
    reason: str


@app.put("/api/criteria")
async def update_criteria(update: CriteriaUpdate):
    """Actualiza un criterio de inversión."""
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    _memory_manager.update_criteria(update.key, update.value, update.reason)
    await ws_manager.broadcast({
        "type": "criteria_update",
        "key": update.key,
        "value": update.value,
    })
    return {"status": "updated", "key": update.key}


@app.get("/api/alerts")
async def get_alerts():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_alerts()


class AlertInput(BaseModel):
    alert_type: str
    message: str
    source: str


@app.post("/api/alerts")
async def add_alert(alert: AlertInput):
    """Agrega una alerta al sistema."""
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    _memory_manager.add_alert(alert.alert_type, alert.message, alert.source)
    await ws_manager.broadcast({
        "type": "new_alert",
        "alert_type": alert.alert_type,
        "message": alert.message,
    })
    return {"status": "added"}


@app.put("/api/alerts/{index}/resolve")
async def resolve_alert(index: int):
    """Resuelve una alerta."""
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    _memory_manager.resolve_alert(index)
    return {"status": "resolved", "index": index}


@app.get("/api/preferences")
async def get_preferences():
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_preferences()


class PreferenceUpdate(BaseModel):
    key: str
    value: Any


@app.put("/api/preferences")
async def update_preference(update: PreferenceUpdate):
    """Actualiza una preferencia del Principal."""
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    _memory_manager.update_preference(update.key, update.value)
    return {"status": "updated", "key": update.key}


@app.get("/api/memory/context")
async def get_macro_context():
    """Retorna el contexto macroeconómico guardado en memoria."""
    if _memory_manager is None:
        raise HTTPException(503, "Memory manager not initialized")
    return _memory_manager.get_macro_context()


# ═══════════════════════════════════════════════════════
# API: System Health
# ═══════════════════════════════════════════════════════

@app.get("/api/health")
async def health_check():
    """Health check del sistema."""
    return {
        "status": "operational",
        "initialized": _orchestrator is not None and _orchestrator._initialized,
        "agent_count": _orchestrator.registry.agent_count if _orchestrator else 0,
        "websocket_clients": len(ws_manager.active_connections),
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@app.get("/api/bus/messages")
async def get_bus_messages(
    msg_type: str | None = None,
    sender: str | None = None,
    limit: int = 50,
):
    """Retorna el log del message bus para auditoría."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")

    from family_office.core.models import AgentRole, MessageType

    mt = None
    if msg_type:
        try:
            mt = MessageType(msg_type)
        except ValueError:
            raise HTTPException(400, f"Invalid message type: {msg_type}")

    sr = None
    if sender:
        try:
            sr = AgentRole(sender)
        except ValueError:
            raise HTTPException(400, f"Invalid agent role: {sender}")

    messages = _orchestrator.bus.get_message_log(msg_type=mt, sender=sr, limit=limit)
    return [
        {
            "id": m.id,
            "type": m.type.value,
            "sender": m.sender.value,
            "recipient": m.recipient.value if m.recipient else None,
            "correlation_id": m.correlation_id,
            "timestamp": m.timestamp.isoformat(),
            "payload_keys": list(m.payload.keys()),
        }
        for m in messages
    ]


# ═══════════════════════════════════════════════════════
# API: Reports (PDF/HTML)
# ═══════════════════════════════════════════════════════

@app.get("/api/reports/decision/{decision_id}")
async def generate_decision_report(decision_id: str):
    """Genera un reporte PDF/HTML de una decisión de inversión."""
    if _decision_store is None:
        raise HTTPException(503, "Decision store not initialized")

    record = _decision_store.get_decision(decision_id)
    if record is None:
        raise HTTPException(404, "Decision not found")

    from family_office.dashboard.report_generator import generate_decision_pdf, HAS_REPORTLAB

    pdf_bytes = generate_decision_pdf(record)

    if HAS_REPORTLAB:
        return Response(
            content=pdf_bytes,
            media_type="application/pdf",
            headers={"Content-Disposition": f"attachment; filename=decision_{decision_id[:8]}.pdf"},
        )
    else:
        return Response(
            content=pdf_bytes,
            media_type="text/html",
            headers={"Content-Disposition": f"attachment; filename=decision_{decision_id[:8]}.html"},
        )


@app.get("/api/reports/portfolio")
async def generate_portfolio_report():
    """Genera un reporte del portfolio actual."""
    if _orchestrator is None:
        raise HTTPException(503, "System not initialized")

    from family_office.core.models import AgentRole
    from family_office.dashboard.report_generator import generate_portfolio_report

    port_ops = _orchestrator.registry.get(AgentRole.PORTFOLIO_OPS)
    if port_ops:
        snapshot = port_ops.get_snapshot()
        html_bytes = generate_portfolio_report(snapshot.model_dump(mode="json"))
        return Response(
            content=html_bytes,
            media_type="text/html",
            headers={"Content-Disposition": "attachment; filename=portfolio_report.html"},
        )
    raise HTTPException(500, "Portfolio Operations not available")

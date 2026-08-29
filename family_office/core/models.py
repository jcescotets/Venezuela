"""
Modelos de datos centrales del Family Office.
Definen la ontología de la organización agéntica.
"""

from __future__ import annotations

import uuid
from datetime import datetime, timezone
from enum import Enum
from typing import Any, Optional

from pydantic import BaseModel, Field


# ---------------------------------------------------------------------------
# Enums
# ---------------------------------------------------------------------------

class AgentLayer(str, Enum):
    DIRECTION = "direction"
    ANALYSIS = "analysis"
    FISCAL = "fiscal"
    RISK = "risk"
    OPERATIONS = "operations"


class AgentRole(str, Enum):
    # Direction
    CIO = "cio"
    HEAD_TAX_STRATEGY = "head_tax_strategy"
    INVESTMENT_COMMITTEE = "investment_committee"
    # Analysis
    MACRO_GEOPOLITICS = "macro_geopolitics"
    FUNDAMENTAL = "fundamental"
    TECHNICAL_QUANT = "technical_quant"
    CREDIT_BONDS = "credit_bonds"
    REAL_ASSETS = "real_assets"
    # Fiscal & Legal
    FISCAL_SPAIN = "fiscal_spain"
    FISCAL_PORTUGAL = "fiscal_portugal"
    FISCAL_PANAMA = "fiscal_panama"
    FISCAL_BARBADOS = "fiscal_barbados"
    FISCAL_US = "fiscal_us"
    FISCAL_VENEZUELA = "fiscal_venezuela"
    CROSS_BORDER = "cross_border"
    # Risk & Control
    RISK_MANAGER = "risk_manager"
    TAX_RISK_AUDIT = "tax_risk_audit"
    # Operations
    PORTFOLIO_OPS = "portfolio_ops"
    OPPORTUNITY_SCANNER = "opportunity_scanner"


class MessageType(str, Enum):
    ANALYSIS_REQUEST = "analysis_request"
    ANALYSIS_REPORT = "analysis_report"
    VETO = "veto"
    VETO_CLEARED = "veto_cleared"
    PROPOSAL = "proposal"
    COMMITTEE_DECISION = "committee_decision"
    DEBATE_CONTRIBUTION = "debate_contribution"
    ALERT = "alert"
    DATA_UPDATE = "data_update"
    USER_DIRECTIVE = "user_directive"


class VetoType(str, Enum):
    RISK_DRAWDOWN = "risk_drawdown"
    RISK_CORRELATION = "risk_correlation"
    RISK_CONCENTRATION = "risk_concentration"
    TAX_RISK = "tax_risk"
    REGULATORY_RISK = "regulatory_risk"
    INDEFENSIBLE_STRUCTURE = "indefensible_structure"


class DecisionStatus(str, Enum):
    PENDING = "pending"
    ANALYZING = "analyzing"
    IN_DEBATE = "in_debate"
    VETOED = "vetoed"
    APPROVED = "approved"
    REJECTED = "rejected"
    AWAITING_USER = "awaiting_user"
    EXECUTED = "executed"


# ---------------------------------------------------------------------------
# Core Models
# ---------------------------------------------------------------------------

class Message(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    type: MessageType
    sender: AgentRole
    recipient: Optional[AgentRole] = None  # None = broadcast
    payload: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    correlation_id: Optional[str] = None  # Link related messages


class AnalysisReport(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_role: AgentRole
    subject: str
    summary: str
    conviction_level: float = Field(ge=0.0, le=1.0)  # 0-1
    key_findings: list[str] = Field(default_factory=list)
    risks_identified: list[str] = Field(default_factory=list)
    data_sources: list[str] = Field(default_factory=list)
    recommendation: Optional[str] = None
    raw_data: dict[str, Any] = Field(default_factory=dict)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class VetoDecision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    agent_role: AgentRole
    proposal_id: str
    veto_type: VetoType
    justification: str
    severity: float = Field(ge=0.0, le=1.0)  # 0 = advisory, 1 = absolute block
    conditions_to_lift: list[str] = Field(default_factory=list)
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FiscalImpact(BaseModel):
    jurisdiction: str
    gross_return_pct: float
    tax_rate_effective: float
    net_return_pct: float
    cfc_risk: bool = False
    permanent_establishment_risk: bool = False
    substance_risk: bool = False
    double_taxation_risk: bool = False
    withholding_tax_pct: float = 0.0
    notes: list[str] = Field(default_factory=list)


class InvestmentProposal(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    title: str
    asset_class: str
    description: str
    amount_usd: float
    expected_gross_return_pct: float
    time_horizon_months: int
    jurisdiction: str
    holding_vehicle: Optional[str] = None
    analyses: list[AnalysisReport] = Field(default_factory=list)
    fiscal_impacts: list[FiscalImpact] = Field(default_factory=list)
    vetoes: list[VetoDecision] = Field(default_factory=list)
    status: DecisionStatus = DecisionStatus.PENDING
    created_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    updated_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class ScenarioAnalysis(BaseModel):
    scenario_base: str
    scenario_optimistic: str
    scenario_adverse: str
    main_risks: list[str]
    recommended_decision: str
    invalidation_conditions: list[str]


class CommitteeDecision(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    proposal_id: str
    agreements: list[str] = Field(default_factory=list)
    contradictions: list[str] = Field(default_factory=list)
    scenarios: Optional[ScenarioAnalysis] = None
    cio_synthesis: str = ""
    final_recommendation: str = ""
    status: DecisionStatus = DecisionStatus.PENDING
    requires_user_approval: bool = True
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ---------------------------------------------------------------------------
# Portfolio Models
# ---------------------------------------------------------------------------

class PortfolioAsset(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    name: str
    ticker: Optional[str] = None
    asset_class: str
    jurisdiction: str
    holding_vehicle: Optional[str] = None
    quantity: float
    cost_basis_usd: float
    current_value_usd: float
    currency: str = "USD"
    acquisition_date: Optional[datetime] = None
    notes: str = ""


class PortfolioSnapshot(BaseModel):
    id: str = Field(default_factory=lambda: str(uuid.uuid4()))
    timestamp: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))
    total_value_usd: float
    assets: list[PortfolioAsset] = Field(default_factory=list)
    allocation_by_class: dict[str, float] = Field(default_factory=dict)
    allocation_by_jurisdiction: dict[str, float] = Field(default_factory=dict)


# ---------------------------------------------------------------------------
# Agent Contract (Instrucción 4 — Definición formal de cada agente)
# ---------------------------------------------------------------------------

class AgentContract(BaseModel):
    """Contrato operativo que define las capacidades y límites de un agente."""
    name: str
    role: AgentRole
    layer: AgentLayer
    specialty: str
    primary_objective: str
    can_recommend: list[str] = Field(default_factory=list)
    can_veto: list[str] = Field(default_factory=list)
    inputs: list[str] = Field(default_factory=list)
    outputs: list[str] = Field(default_factory=list)
    reports_to: list[AgentRole] = Field(default_factory=list)
    interacts_with: list[AgentRole] = Field(default_factory=list)
    restrictions: list[str] = Field(default_factory=list)

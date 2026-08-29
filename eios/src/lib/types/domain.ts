/**
 * EIOS Domain Types — Business logic types beyond the database schema.
 * Aligned with Vol I principles: source-first, deterministic-first.
 */

export type Currency = "USD" | "EUR" | "GBP" | "CHF" | "VES" | "BRL";

export type RiskLevel = "low" | "medium" | "high" | "critical";

export interface MoneyAmount {
  value: number;
  currency: Currency;
}

export interface PortfolioSummary {
  totalValue: MoneyAmount;
  totalCostBasis: MoneyAmount;
  unrealizedPnl: MoneyAmount;
  unrealizedPnlPct: number;
  positionCount: number;
  allocationByType: Record<string, number>;
  asOfDate: string;
}

export interface DecisionPipeline {
  phase:
    | "intake"
    | "screening"
    | "analysis"
    | "fiscal_review"
    | "risk_assessment"
    | "governance"
    | "execution";
  vetoed: boolean;
  vetoReason?: string;
  analyses: AnalysisResult[];
}

export interface AnalysisResult {
  module: string;
  score: number;
  confidence: number;
  summary: string;
  details: Record<string, unknown>;
  sources: string[];
}

export interface FiscalAssessment {
  jurisdiction: string;
  cfcRisk: RiskLevel;
  substanceScore: number;
  treatyApplicable: boolean;
  withholdingRate: number;
  effectiveTaxRate: number;
  recommendations: string[];
}

export interface RiskAlert {
  id: string;
  level: RiskLevel;
  category: "market" | "credit" | "liquidity" | "concentration" | "regulatory" | "fiscal";
  title: string;
  description: string;
  affectedEntities: string[];
  suggestedAction: string;
  createdAt: string;
}

export const EIOS_MODULES = [
  "identity",
  "portfolio",
  "intelligence",
  "documents",
  "decisions",
  "risk",
  "fiscal",
  "corporate",
  "knowledge",
  "reporting",
] as const;

export type EIOSModule = (typeof EIOS_MODULES)[number];

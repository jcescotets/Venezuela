import { Header } from "@/components/layout/header";

export default function PortfolioPage() {
  return (
    <div>
      <Header
        title="Portfolio"
        description="Wealth & Portfolio Ledger — Posiciones, transacciones y valoracion consolidada."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Portfolio — Sprint 1
          </p>
        </div>
      </div>
    </div>
  );
}

import { Header } from "@/components/layout/header";

export default function RiskPage() {
  return (
    <div>
      <Header
        title="Riesgo"
        description="Risk & Alerts — Monitoreo de riesgos de mercado, credito, liquidez y concentracion."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Risk — Sprint 9
          </p>
        </div>
      </div>
    </div>
  );
}

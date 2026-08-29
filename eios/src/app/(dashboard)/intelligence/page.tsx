import { Header } from "@/components/layout/header";

export default function IntelligencePage() {
  return (
    <div>
      <Header
        title="Intelligence"
        description="Investment Intelligence — Analisis de mercado, screening y due diligence."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Intelligence — Sprint 4
          </p>
        </div>
      </div>
    </div>
  );
}

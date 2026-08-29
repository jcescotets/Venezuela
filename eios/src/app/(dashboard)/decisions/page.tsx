import { Header } from "@/components/layout/header";

export default function DecisionsPage() {
  return (
    <div>
      <Header
        title="Decisiones"
        description="Decision & Governance — Pipeline de 7 fases con veto gate."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Decisions — Sprint 7
          </p>
        </div>
      </div>
    </div>
  );
}

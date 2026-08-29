import { Header } from "@/components/layout/header";

export default function CorporatePage() {
  return (
    <div>
      <Header
        title="Corporativo"
        description="Corporate Intelligence — Estructura societaria, UBOs y compliance."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Corporate — Sprint 14
          </p>
        </div>
      </div>
    </div>
  );
}

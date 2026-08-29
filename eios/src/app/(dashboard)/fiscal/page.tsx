import { Header } from "@/components/layout/header";

export default function FiscalPage() {
  return (
    <div>
      <Header
        title="Fiscal"
        description="Fiscal Intelligence — CFC, sustancia, tratados, WHT y tasa efectiva."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Fiscal — Sprint 11
          </p>
        </div>
      </div>
    </div>
  );
}

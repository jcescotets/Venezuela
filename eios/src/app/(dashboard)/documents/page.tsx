import { Header } from "@/components/layout/header";

export default function DocumentsPage() {
  return (
    <div>
      <Header
        title="Documentos"
        description="Document Intelligence — Gestion documental, OCR y busqueda semantica."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Documents — Sprint 5
          </p>
        </div>
      </div>
    </div>
  );
}

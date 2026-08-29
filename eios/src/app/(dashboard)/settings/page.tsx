import { Header } from "@/components/layout/header";

export default function SettingsPage() {
  return (
    <div>
      <Header
        title="Configuracion"
        description="Organizacion, usuarios, permisos y preferencias."
      />
      <div className="p-6">
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-sm text-gray-500">
            Modulo Settings — Sprint 2
          </p>
        </div>
      </div>
    </div>
  );
}

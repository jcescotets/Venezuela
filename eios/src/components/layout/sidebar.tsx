"use client";

import { usePathname } from "next/navigation";
import {
  Building2,
  Briefcase,
  Brain,
  FileText,
  Scale,
  ShieldAlert,
  Landmark,
  Network,
  BookOpen,
  BarChart3,
  Settings,
  LogOut,
} from "lucide-react";
import { NavItem } from "./nav-item";
import { createBrowserSupabaseClient } from "@/lib/supabase/client";

const modules = [
  { href: "/portfolio", label: "Portfolio", icon: Briefcase },
  { href: "/intelligence", label: "Intelligence", icon: Brain },
  { href: "/documents", label: "Documentos", icon: FileText },
  { href: "/decisions", label: "Decisiones", icon: Scale },
  { href: "/risk", label: "Riesgo", icon: ShieldAlert },
  { href: "/fiscal", label: "Fiscal", icon: Landmark },
  { href: "/corporate", label: "Corporativo", icon: Network },
  { href: "/settings", label: "Configuracion", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  async function handleLogout() {
    const supabase = createBrowserSupabaseClient();
    await supabase.auth.signOut();
    window.location.href = "/login";
  }

  return (
    <aside className="flex h-screen w-56 flex-col border-r border-gray-200 bg-white">
      <div className="flex h-14 items-center border-b border-gray-200 px-4">
        <Building2 className="mr-2 h-5 w-5 text-brand-600" />
        <span className="text-sm font-bold text-gray-900">EIOS</span>
      </div>

      <nav className="flex-1 overflow-y-auto px-2 py-3">
        <ul className="space-y-0.5">
          {modules.map((m) => (
            <li key={m.href}>
              <NavItem
                href={m.href}
                label={m.label}
                icon={m.icon}
                active={pathname.startsWith(m.href)}
              />
            </li>
          ))}
        </ul>
      </nav>

      <div className="border-t border-gray-200 p-2">
        <button
          onClick={handleLogout}
          className="flex w-full items-center gap-2 rounded-md px-3 py-2 text-sm text-gray-500 hover:bg-gray-100 hover:text-gray-700"
        >
          <LogOut className="h-4 w-4" />
          Cerrar Sesion
        </button>
      </div>
    </aside>
  );
}

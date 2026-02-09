#!/usr/bin/env python3
"""
Family Office — Entry Point
============================
CLI y servidor del Family Office Agéntico.

Uso:
    python main.py                    # Inicia el dashboard web
    python main.py --cli              # Modo interactivo CLI
    python main.py --org              # Muestra la organización
    python main.py --analyze "título" # Análisis rápido
"""

from __future__ import annotations

import argparse
import asyncio
import logging
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))

from family_office.config.settings import settings
from family_office.orchestrator import FamilyOfficeOrchestrator


def setup_logging():
    logging.basicConfig(
        level=getattr(logging, settings.log_level),
        format="%(asctime)s | %(name)-30s | %(levelname)-7s | %(message)s",
        datefmt="%H:%M:%S",
    )


def print_banner():
    print("""
╔══════════════════════════════════════════════════════════╗
║              FAMILY OFFICE — SISTEMA AGÉNTICO           ║
║                                                          ║
║  Organización agéntica permanente para inversión,        ║
║  preservación de patrimonio y control de riesgo.         ║
║                                                          ║
║  20 agentes | 5 capas | Debate estructurado | Veto      ║
╚══════════════════════════════════════════════════════════╝
""")


async def run_dashboard(orchestrator: FamilyOfficeOrchestrator):
    """Inicia el dashboard web con FastAPI + Uvicorn."""
    import uvicorn
    from family_office.dashboard.api import app, set_services

    set_services(
        orchestrator=orchestrator,
        market_svc=orchestrator.market_data,
        macro_svc=orchestrator.macro_data,
        decision_store=orchestrator.decision_store,
        memory_mgr=orchestrator.memory,
    )

    config = uvicorn.Config(
        app,
        host=settings.dashboard.host,
        port=settings.dashboard.port,
        log_level=settings.log_level.lower(),
    )
    server = uvicorn.Server(config)
    print(f"\n  Dashboard: http://localhost:{settings.dashboard.port}")
    print(f"  API docs:  http://localhost:{settings.dashboard.port}/docs\n")
    await server.serve()


async def run_cli(orchestrator: FamilyOfficeOrchestrator):
    """Modo interactivo CLI."""
    from family_office.core.models import AgentRole, InvestmentProposal

    print("\nModo CLI interactivo. Comandos:")
    print("  org           — Ver organización")
    print("  macro         — Briefing macro")
    print("  scan          — Scan de oportunidades")
    print("  analyze       — Nuevo análisis de inversión")
    print("  portfolio     — Ver portfolio")
    print("  criteria      — Ver criterios de inversión")
    print("  quit          — Salir\n")

    while True:
        try:
            cmd = input("FamilyOffice> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\nSaliendo...")
            break

        if cmd == "quit" or cmd == "exit":
            break
        elif cmd == "org":
            print(orchestrator.get_organization_summary())
        elif cmd == "macro":
            print("Obteniendo briefing macro...")
            result = await orchestrator.get_macro_briefing()
            print_result(result)
        elif cmd == "scan":
            print("Escaneando oportunidades...")
            result = await orchestrator.scan_opportunities()
            print_result(result)
        elif cmd == "analyze":
            title = input("  Título: ").strip()
            asset_class = input("  Clase de activo: ").strip() or "Renta Variable"
            amount = float(input("  Monto USD: ").strip() or "100000")
            ret = float(input("  Retorno bruto esperado %: ").strip() or "10")
            jurisdiction = input("  Jurisdicción: ").strip() or "global"
            horizon = int(input("  Horizonte (meses): ").strip() or "12")

            proposal = InvestmentProposal(
                title=title,
                asset_class=asset_class,
                description=f"Análisis solicitado por el Principal: {title}",
                amount_usd=amount,
                expected_gross_return_pct=ret,
                time_horizon_months=horizon,
                jurisdiction=jurisdiction,
            )

            print("\nEjecutando pipeline completo...")
            print("  → Análisis independiente (5 agentes)")
            print("  → Evaluación fiscal (7 jurisdicciones)")
            print("  → Debate del Comité de Inversión")
            print("  → Evaluación de riesgo (veto gate)")
            print("  → Síntesis del CIO\n")

            result = await orchestrator.process_proposal(proposal)
            report = orchestrator.pipeline.format_principal_report(result)
            print(report)
        elif cmd == "portfolio":
            from family_office.core.models import AgentRole
            port_ops = orchestrator.registry.get(AgentRole.PORTFOLIO_OPS)
            if port_ops:
                snapshot = port_ops.get_snapshot()
                print(f"\nValor total: USD {snapshot.total_value_usd:,.0f}")
                print(f"Posiciones: {len(snapshot.assets)}")
                for a in snapshot.assets:
                    print(f"  {a.name}: USD {a.current_value_usd:,.0f} ({a.asset_class}, {a.jurisdiction})")
            else:
                print("Portfolio Operations no disponible")
        elif cmd == "criteria":
            criteria = orchestrator.memory.get_criteria()
            print_result(criteria)
        elif cmd == "help":
            print("Comandos: org, macro, scan, analyze, portfolio, criteria, quit")
        else:
            print(f"Comando no reconocido: {cmd}. Escribe 'help' para ver opciones.")


def print_result(data):
    """Pretty-print de resultados."""
    import json
    if isinstance(data, dict):
        # Filter out very long values for readability
        filtered = {}
        for k, v in data.items():
            if isinstance(v, str) and len(v) > 500:
                filtered[k] = v[:500] + "..."
            else:
                filtered[k] = v
        print(json.dumps(filtered, indent=2, default=str, ensure_ascii=False))
    else:
        print(data)


def main():
    parser = argparse.ArgumentParser(description="Family Office Agentic System")
    parser.add_argument("--cli", action="store_true", help="Interactive CLI mode")
    parser.add_argument("--org", action="store_true", help="Show organization")
    parser.add_argument("--port", type=int, default=None, help="Dashboard port")
    args = parser.parse_args()

    setup_logging()
    print_banner()

    orchestrator = FamilyOfficeOrchestrator()
    orchestrator.initialize()

    if args.org:
        print(orchestrator.get_organization_summary())
        return

    if args.port:
        settings.dashboard.port = args.port

    if args.cli:
        asyncio.run(run_cli(orchestrator))
    else:
        asyncio.run(run_dashboard(orchestrator))


if __name__ == "__main__":
    main()

# EIOS — Escotet Intelligence OS

Family Office Intelligence Platform.

## Stack

- **Frontend**: Next.js 14 (App Router) + TypeScript + Tailwind CSS
- **Backend**: Supabase (PostgreSQL + Auth + RLS + Storage)
- **Deploy**: Vercel

## Quick Start

```bash
cp .env.example .env.local
# Fill in Supabase credentials
npm install
npm run dev
```

## Modules

| Module | Description | Sprint |
|--------|-------------|--------|
| Portfolio | Wealth & Portfolio Ledger | 1 |
| Intelligence | Investment Intelligence | 4 |
| Documents | Document Intelligence | 5 |
| Decisions | Decision & Governance | 7 |
| Risk | Risk & Alerts | 9 |
| Fiscal | Fiscal Intelligence | 11 |
| Corporate | Corporate Intelligence | 14 |
| Knowledge | Knowledge Graph | 17 |
| Reporting | Reporting & Analytics | 20 |
| Settings | Organization & Users | 2 |

## Database

Foundation schema: `supabase/migrations/00001_foundation.sql`

9 tables with RLS:
organizations, profiles, entities, portfolios, positions, transactions, decisions, documents, audit_log

## Architecture Principles

1. Human-in-the-loop
2. Source-first
3. Deterministic-first
4. AI-assisted (not AI-dependent)
5. Full auditability
6. Privacy by design
7. Modular
8. Portable
9. Explainable
10. Progressive assurance

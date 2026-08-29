-- EIOS Foundation Schema — Sprint 0
-- 9 core tables with RLS policies
-- Aligned with Vol III Technical Architecture

-- Extensions
create extension if not exists "uuid-ossp";
create extension if not exists "pgcrypto";

-- Enums
create type org_type as enum ('family_office', 'holding', 'trust', 'foundation');
create type user_role as enum ('owner', 'advisor', 'viewer', 'admin');
create type entity_type as enum ('natural_person', 'company', 'trust', 'fund', 'spv');
create type asset_type as enum ('equity', 'fixed_income', 'fund', 'real_estate', 'private_equity', 'cash', 'derivative', 'crypto');
create type tx_type as enum ('buy', 'sell', 'dividend', 'coupon', 'fee', 'transfer');
create type decision_status as enum ('draft', 'analysis', 'review', 'approved', 'rejected', 'executed');
create type decision_type as enum ('investment', 'fiscal', 'corporate', 'risk');

-- Organizations
create table organizations (
  id uuid primary key default uuid_generate_v4(),
  name text not null,
  type org_type not null default 'family_office',
  jurisdiction text,
  tax_id text,
  metadata jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Profiles (linked to auth.users)
create table profiles (
  id uuid primary key default uuid_generate_v4(),
  user_id uuid not null references auth.users(id) on delete cascade,
  organization_id uuid not null references organizations(id) on delete cascade,
  role user_role not null default 'viewer',
  full_name text not null,
  email text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique(user_id, organization_id)
);

create index idx_profiles_user on profiles(user_id);
create index idx_profiles_org on profiles(organization_id);

-- Entities (legal persons within an organization)
create table entities (
  id uuid primary key default uuid_generate_v4(),
  organization_id uuid not null references organizations(id) on delete cascade,
  name text not null,
  type entity_type not null,
  jurisdiction text not null,
  tax_id text,
  incorporation_date date,
  metadata jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_entities_org on entities(organization_id);

-- Portfolios
create table portfolios (
  id uuid primary key default uuid_generate_v4(),
  organization_id uuid not null references organizations(id) on delete cascade,
  entity_id uuid not null references entities(id) on delete cascade,
  name text not null,
  currency text not null default 'USD',
  custodian text,
  account_number text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_portfolios_org on portfolios(organization_id);
create index idx_portfolios_entity on portfolios(entity_id);

-- Positions
create table positions (
  id uuid primary key default uuid_generate_v4(),
  portfolio_id uuid not null references portfolios(id) on delete cascade,
  asset_type asset_type not null,
  symbol text,
  isin text,
  name text not null,
  quantity numeric not null default 0,
  cost_basis numeric not null default 0,
  cost_basis_currency text not null default 'USD',
  current_price numeric,
  current_value numeric,
  unrealized_pnl numeric,
  metadata jsonb,
  as_of_date date not null default current_date,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_positions_portfolio on positions(portfolio_id);
create index idx_positions_symbol on positions(symbol) where symbol is not null;

-- Transactions
create table transactions (
  id uuid primary key default uuid_generate_v4(),
  portfolio_id uuid not null references portfolios(id) on delete cascade,
  position_id uuid references positions(id) on delete set null,
  type tx_type not null,
  quantity numeric,
  price numeric,
  amount numeric not null,
  currency text not null default 'USD',
  executed_at timestamptz not null,
  settlement_date date,
  notes text,
  metadata jsonb,
  created_at timestamptz not null default now()
);

create index idx_tx_portfolio on transactions(portfolio_id);
create index idx_tx_executed on transactions(executed_at);

-- Decisions
create table decisions (
  id uuid primary key default uuid_generate_v4(),
  organization_id uuid not null references organizations(id) on delete cascade,
  title text not null,
  status decision_status not null default 'draft',
  decision_type decision_type not null,
  summary text,
  analysis jsonb,
  risk_assessment jsonb,
  fiscal_impact jsonb,
  approved_by uuid references profiles(id),
  approved_at timestamptz,
  created_by uuid not null references profiles(id),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index idx_decisions_org on decisions(organization_id);
create index idx_decisions_status on decisions(status);

-- Documents
create table documents (
  id uuid primary key default uuid_generate_v4(),
  organization_id uuid not null references organizations(id) on delete cascade,
  entity_id uuid references entities(id) on delete set null,
  title text not null,
  file_path text not null,
  mime_type text not null,
  size_bytes bigint not null default 0,
  doc_type text,
  extracted_text text,
  embedding vector(1536),
  metadata jsonb,
  uploaded_by uuid not null references profiles(id),
  created_at timestamptz not null default now()
);

create index idx_documents_org on documents(organization_id);

-- Audit log (append-only)
create table audit_log (
  id uuid primary key default uuid_generate_v4(),
  organization_id uuid not null references organizations(id) on delete cascade,
  user_id uuid not null,
  action text not null,
  resource_type text not null,
  resource_id text not null,
  details jsonb,
  ip_address inet,
  created_at timestamptz not null default now()
);

create index idx_audit_org on audit_log(organization_id);
create index idx_audit_created on audit_log(created_at);

-- Updated_at trigger
create or replace function update_updated_at()
returns trigger as $$
begin
  new.updated_at = now();
  return new;
end;
$$ language plpgsql;

create trigger trg_organizations_updated before update on organizations for each row execute function update_updated_at();
create trigger trg_profiles_updated before update on profiles for each row execute function update_updated_at();
create trigger trg_entities_updated before update on entities for each row execute function update_updated_at();
create trigger trg_portfolios_updated before update on portfolios for each row execute function update_updated_at();
create trigger trg_positions_updated before update on positions for each row execute function update_updated_at();
create trigger trg_decisions_updated before update on decisions for each row execute function update_updated_at();

-- RLS: enable on all tables
alter table organizations enable row level security;
alter table profiles enable row level security;
alter table entities enable row level security;
alter table portfolios enable row level security;
alter table positions enable row level security;
alter table transactions enable row level security;
alter table decisions enable row level security;
alter table documents enable row level security;
alter table audit_log enable row level security;

-- RLS policies: users see only their organization's data
create policy "Users see own org"
  on organizations for select
  using (id in (select organization_id from profiles where user_id = auth.uid()));

create policy "Users see own profile"
  on profiles for select
  using (user_id = auth.uid());

create policy "Users see org entities"
  on entities for select
  using (organization_id in (select organization_id from profiles where user_id = auth.uid()));

create policy "Users see org portfolios"
  on portfolios for select
  using (organization_id in (select organization_id from profiles where user_id = auth.uid()));

create policy "Users see portfolio positions"
  on positions for select
  using (portfolio_id in (
    select p.id from portfolios p
    join profiles pr on pr.organization_id = p.organization_id
    where pr.user_id = auth.uid()
  ));

create policy "Users see portfolio transactions"
  on transactions for select
  using (portfolio_id in (
    select p.id from portfolios p
    join profiles pr on pr.organization_id = p.organization_id
    where pr.user_id = auth.uid()
  ));

create policy "Users see org decisions"
  on decisions for select
  using (organization_id in (select organization_id from profiles where user_id = auth.uid()));

create policy "Users see org documents"
  on documents for select
  using (organization_id in (select organization_id from profiles where user_id = auth.uid()));

create policy "Users see org audit"
  on audit_log for select
  using (organization_id in (select organization_id from profiles where user_id = auth.uid()));

-- Phase 5: one row per AI request, for the admin usage page (by provider/model, cost, cache hit rate,
-- fallback rate, latency). usage_daily keeps the per-user counters used for quotas.
create table llm_calls (
  id bigint generated always as identity primary key,
  user_id uuid references profiles (id) on delete set null,
  created_at timestamptz not null default now(),
  purpose text not null check (char_length(purpose) between 1 and 40),
  provider text not null,
  model text not null,
  tokens_in integer not null default 0 check (tokens_in >= 0),
  tokens_out integer not null default 0 check (tokens_out >= 0),
  est_cost_usd numeric(12, 6) not null default 0 check (est_cost_usd >= 0),
  latency_ms integer not null default 0 check (latency_ms >= 0),
  cached boolean not null default false,
  fallback_used boolean not null default false
);
create index llm_calls_created_idx on llm_calls (created_at desc);
create index llm_calls_user_idx on llm_calls (user_id, created_at desc);

-- Backend-only, like global_usage_daily: RLS on, nothing granted to browser roles.
alter table llm_calls enable row level security;
revoke all on llm_calls from anon, authenticated;

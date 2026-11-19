-- Part 5: graph proposals, study mode, evaluation, settings and the audit log.

create table graph_proposals (
  id uuid primary key default gen_random_uuid(),
  type proposal_type not null,
  payload jsonb not null,
  rationale text,
  confidence numeric(4, 3) check (confidence is null or confidence between 0 and 1),
  status proposal_status not null default 'pending',
  proposed_by proposer not null,
  reviewer_id uuid references profiles (id) on delete set null,
  decided_at timestamptz,
  note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index graph_proposals_status_idx on graph_proposals (status, created_at desc);

-- Singleton row (id is always 1) controlling the user study.
create table study_settings (
  id smallint primary key default 1 check (id = 1),
  enabled boolean not null default false,
  assignment assignment_mode not null default 'random',
  pretest_set_id text,
  posttest_set_id text,
  started_at timestamptz,
  updated_at timestamptz not null default now()
);
insert into study_settings (id) values (1) on conflict do nothing;

create table eval_runs (
  id uuid primary key default gen_random_uuid(),
  name text not null,
  config jsonb not null default '{}'::jsonb,
  summary jsonb,
  started_at timestamptz not null default now(),
  finished_at timestamptz,
  created_by uuid references profiles (id) on delete set null
);

create table eval_results (
  id uuid primary key default gen_random_uuid(),
  run_id uuid not null references eval_runs (id) on delete cascade,
  item_id text not null,
  mode retrieval_mode not null,
  question text not null,
  answer text,
  contexts jsonb,
  metrics jsonb,
  latency_ms integer,
  tokens_in integer,
  tokens_out integer,
  created_at timestamptz not null default now(),
  unique (run_id, item_id, mode)
);

-- Editable settings: quota defaults, global daily cap, feature flags.
create table app_settings (
  key text primary key,
  value jsonb not null,
  updated_at timestamptz not null default now(),
  updated_by uuid references profiles (id) on delete set null
);

create table audit_log (
  id bigint generated always as identity primary key,
  actor uuid references profiles (id) on delete set null,
  action text not null,
  target text,
  details jsonb,
  created_at timestamptz not null default now()
);
create index audit_log_created_idx on audit_log (created_at desc);

create trigger graph_proposals_updated_at before update on graph_proposals for each row execute function set_updated_at();
create trigger study_settings_updated_at before update on study_settings for each row execute function set_updated_at();
create trigger app_settings_updated_at before update on app_settings for each row execute function set_updated_at();

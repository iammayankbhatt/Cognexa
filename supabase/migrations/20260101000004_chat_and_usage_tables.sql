-- Part 4: tutor chat, feedback, usage metering and the response cache.

create table chat_threads (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  title text not null default 'New chat' check (char_length(title) <= 200),
  archived boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index chat_threads_user_idx on chat_threads (user_id, archived, updated_at desc);

create table chat_messages (
  id uuid primary key default gen_random_uuid(),
  thread_id uuid not null references chat_threads (id) on delete cascade,
  user_id uuid not null references profiles (id) on delete cascade,
  role message_role not null,
  content text not null,
  mode retrieval_mode,
  matched_concepts jsonb,
  retrieval_trace jsonb,
  provider text,
  model text,
  tokens_in integer check (tokens_in is null or tokens_in >= 0),
  tokens_out integer check (tokens_out is null or tokens_out >= 0),
  latency_ms integer check (latency_ms is null or latency_ms >= 0),
  cached boolean not null default false,
  created_at timestamptz not null default now()
);
create index chat_messages_thread_idx on chat_messages (thread_id, created_at);
create index chat_messages_user_idx on chat_messages (user_id, created_at desc);

create table message_feedback (
  id uuid primary key default gen_random_uuid(),
  message_id uuid not null references chat_messages (id) on delete cascade,
  user_id uuid not null references profiles (id) on delete cascade,
  rating smallint check (rating is null or rating in (-1, 1)),
  report_reason report_reason,
  comment text check (comment is null or char_length(comment) <= 2000),
  status feedback_status not null default 'open',
  resolved_by uuid references profiles (id) on delete set null,
  resolution_note text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (message_id, user_id)
);
create index message_feedback_status_idx on message_feedback (status, created_at desc);

create table usage_daily (
  user_id uuid not null references profiles (id) on delete cascade,
  date date not null,
  ai_requests integer not null default 0 check (ai_requests >= 0),
  tokens_in bigint not null default 0 check (tokens_in >= 0),
  tokens_out bigint not null default 0 check (tokens_out >= 0),
  est_cost_usd numeric(12, 6) not null default 0 check (est_cost_usd >= 0),
  primary key (user_id, date)
);

create table global_usage_daily (
  date date primary key,
  ai_requests integer not null default 0 check (ai_requests >= 0),
  tokens_in bigint not null default 0 check (tokens_in >= 0),
  tokens_out bigint not null default 0 check (tokens_out >= 0)
);

create table response_cache (
  key_hash text primary key,
  payload jsonb not null,
  concept_ids text[] not null default '{}',
  created_at timestamptz not null default now(),
  expires_at timestamptz not null,
  hits integer not null default 0 check (hits >= 0),
  invalidated boolean not null default false
);
create index response_cache_expiry_idx on response_cache (expires_at);
create index response_cache_concepts_idx on response_cache using gin (concept_ids);

create trigger chat_threads_updated_at before update on chat_threads for each row execute function set_updated_at();
create trigger message_feedback_updated_at before update on message_feedback for each row execute function set_updated_at();

-- Part 3: quizzes, mastery, notes, revision sheets and recommendation logging.

create table quiz_sessions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  mode quiz_mode not null,
  concept_id text references concepts (id) on delete set null,
  started_at timestamptz not null default now(),
  submitted_at timestamptz,
  score numeric(8, 3),
  max_score numeric(8, 3),
  time_limit_s integer check (time_limit_s is null or time_limit_s > 0),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index quiz_sessions_user_idx on quiz_sessions (user_id, started_at desc);

create table quiz_answers (
  id uuid primary key default gen_random_uuid(),
  session_id uuid not null references quiz_sessions (id) on delete cascade,
  user_id uuid not null references profiles (id) on delete cascade,
  question_id text not null references questions (id) on delete cascade,
  response jsonb not null,
  is_correct boolean,
  score numeric(4, 3) check (score is null or score between 0 and 1),
  feedback text,
  graded_by grader not null default 'auto',
  time_ms integer check (time_ms is null or time_ms >= 0),
  created_at timestamptz not null default now(),
  unique (session_id, question_id)
);
create index quiz_answers_user_idx on quiz_answers (user_id, created_at desc);
create index quiz_answers_question_idx on quiz_answers (question_id);

create table mastery (
  user_id uuid not null references profiles (id) on delete cascade,
  concept_id text not null references concepts (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  score numeric(4, 3) not null default 0 check (score between 0 and 1),
  attempts integer not null default 0 check (attempts >= 0),
  correct integer not null default 0 check (correct >= 0),
  last_practiced_at timestamptz,
  next_review_at timestamptz,
  ease numeric(4, 2) not null default 2.5 check (ease >= 1.3),
  updated_at timestamptz not null default now(),
  primary key (user_id, concept_id),
  check (correct <= attempts)
);
create index mastery_review_idx on mastery (user_id, next_review_at);
create index mastery_subject_idx on mastery (subject_id);

create table notes (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  concept_id text not null references concepts (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  body text not null default '' check (char_length(body) <= 20000),
  bookmarked boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  unique (user_id, concept_id)
);

create table revision_sheets (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  concept_ids text[] not null default '{}',
  content text not null,
  created_at timestamptz not null default now()
);
create index revision_sheets_user_idx on revision_sheets (user_id, created_at desc);

create table recommendations_log (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references profiles (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  concept_id text not null references concepts (id) on delete cascade,
  reason_code text not null,
  reason_text text not null,
  path jsonb,
  study_group study_group not null default 'none',
  shown_at timestamptz not null default now(),
  clicked_at timestamptz,
  completed_at timestamptz
);
create index recommendations_log_user_idx on recommendations_log (user_id, shown_at desc);

create trigger quiz_sessions_updated_at before update on quiz_sessions for each row execute function set_updated_at();
create trigger mastery_updated_at before update on mastery for each row execute function set_updated_at();
create trigger notes_updated_at before update on notes for each row execute function set_updated_at();

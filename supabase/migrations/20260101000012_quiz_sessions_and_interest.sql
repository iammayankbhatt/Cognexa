-- Phase 8: quiz session contents, short-answer grading state, and the "questions asked" signal.

-- Which questions a session served (in order) and how feedback is shown.
alter table quiz_sessions
  add column question_ids text[] not null default '{}',
  add column feedback_mode text not null default 'immediate'
    check (feedback_mode in ('immediate', 'exam'));

-- Short answers whose LLM grading could not run yet (provider down or quota): graded on retry.
alter table quiz_answers
  add column pending boolean not null default false,
  add column details jsonb;

-- Concepts a student asked the tutor about (one row per matched concept per question), used by
-- the Phase 9 recommender ("questions asked", report abstract).
create table concept_interest (
  id bigint generated always as identity primary key,
  user_id uuid not null references profiles (id) on delete cascade,
  concept_id text not null references concepts (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  source text not null default 'tutor' check (source in ('tutor', 'quiz', 'learn')),
  asked_at timestamptz not null default now()
);
create index concept_interest_user_idx on concept_interest (user_id, asked_at desc);
create index concept_interest_concept_idx on concept_interest (concept_id);

alter table concept_interest enable row level security;
create policy concept_interest_select_own on concept_interest for select to authenticated
  using (user_id = auth.uid());

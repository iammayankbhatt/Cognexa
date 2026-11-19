-- Cognexa schema, part 1: extensions, enums and shared helper functions.
-- Applies on Supabase AND on plain Postgres + pgvector (CI). Plain Postgres needs supabase/shim/auth_shim.sql first
-- (scripts/migrate.py applies it automatically when the auth schema is missing).

create extension if not exists vector;

create type user_role as enum ('student', 'reviewer', 'admin');
create type study_group as enum ('adaptive', 'baseline', 'none');
create type question_type as enum ('mcq', 'multi_select', 'true_false', 'code_output', 'short_answer');
create type quiz_mode as enum ('concept', 'adaptive', 'review', 'diagnostic', 'pretest', 'posttest');
create type grader as enum ('auto', 'llm');
create type message_role as enum ('user', 'assistant', 'system');
create type retrieval_mode as enum ('graphrag', 'plain_rag');
create type report_reason as enum ('incorrect', 'incomplete', 'off_topic', 'harmful', 'other');
create type feedback_status as enum ('open', 'reviewing', 'resolved', 'dismissed');
create type proposal_type as enum ('add_edge', 'remove_edge', 'tag_chunk', 'new_concept');
create type proposal_status as enum ('pending', 'approved', 'rejected');
create type proposer as enum ('llm', 'user');
create type assignment_mode as enum ('random', 'alternate');

-- Keeps updated_at current on every UPDATE.
create or replace function set_updated_at() returns trigger
language plpgsql as $$
begin
  new.updated_at = now();
  return new;
end;
$$;

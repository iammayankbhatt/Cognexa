-- Phase 11: admin console (graph editor, LLM proposals, document ingestion, content editor,
-- moderation, account disabling).

-- Where a chunk came from. Seeding from data/subjects only replaces 'notes' chunks, so chunks
-- approved from LLM proposals ('llm') or written in the admin editor ('admin') survive a re-seed.
alter table content_chunks
  add column source text not null default 'notes' check (source in ('notes', 'llm', 'admin'));

-- Reviewers mark questions as checked, like chunks.
alter table questions add column reviewed boolean not null default false;

-- Uploaded lecture notes whose sections were turned into proposals.
create table ingest_documents (
  id uuid primary key default gen_random_uuid(),
  subject_id text not null references subjects (id) on delete cascade,
  filename text not null check (char_length(filename) between 1 and 255),
  media_type text not null,
  size_bytes integer not null check (size_bytes >= 0),
  pages integer,
  sections integer not null default 0,
  proposals integer not null default 0,
  status text not null default 'processing' check (status in ('processing', 'done', 'failed')),
  error text,
  uploaded_by uuid references profiles (id) on delete set null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index ingest_documents_created_idx on ingest_documents (created_at desc);
create trigger ingest_documents_updated_at before update on ingest_documents
  for each row execute function set_updated_at();
alter table ingest_documents enable row level security;
revoke all on ingest_documents from anon, authenticated;

-- Pending proposals are listed by type and confidence.
create index graph_proposals_type_idx on graph_proposals (status, type, confidence desc);

-- Disabled accounts keep their data but every API call is refused.
alter table profiles add column disabled_at timestamptz;

create or replace function prevent_profile_privilege_change() returns trigger
language plpgsql as $$
begin
  if current_user in ('authenticated', 'anon') then
    if new.role is distinct from old.role
       or new.quota_override is distinct from old.quota_override
       or new.study_group is distinct from old.study_group
       or new.study_enrolled_at is distinct from old.study_enrolled_at
       or new.study_consent_at is distinct from old.study_consent_at
       or new.study_withdrawn_at is distinct from old.study_withdrawn_at
       or new.disabled_at is distinct from old.disabled_at then
      raise exception 'role, quota, study and account fields can only be changed by the backend'
        using errcode = '42501';
    end if;
  end if;
  return new;
end;
$$;

-- Part 2: profiles and the content tables (subjects, concepts, chunks, questions).
-- Every concept, question, chunk and mastery row carries subject_id so other subjects can be added as content packs.

create table profiles (
  id uuid primary key references auth.users (id) on delete cascade,
  display_name text,
  role user_role not null default 'student',
  theme text not null default 'neon-noir'
    check (theme in ('neon-noir', 'titanium-dark', 'titanium-light')),
  study_group study_group not null default 'none',
  onboarding_completed boolean not null default false,
  quota_override jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create table subjects (
  id text primary key,
  name text not null,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

-- Mirror of the Neo4j concept nodes, for foreign keys and fast lookups.
create table concepts (
  id text primary key,
  subject_id text not null references subjects (id) on delete cascade,
  name text not null,
  cluster text not null,
  difficulty smallint not null check (difficulty between 1 and 5),
  order_index integer not null default 0,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index concepts_subject_idx on concepts (subject_id, order_index);

-- Retrievable content chunks. embedding dimension is fixed at 768 in SQL (EMBEDDING_DIM must match).
-- To change it: add a new migration "alter table content_chunks alter column embedding type vector(N)"
-- (existing embeddings must be cleared first), set EMBEDDING_DIM=N and re-run scripts/seed_vectors.py.
create table content_chunks (
  id text primary key,
  concept_id text not null references concepts (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  kind text not null,
  heading text not null default '',
  text text not null,
  "order" integer not null default 0,
  embedding vector(768),
  reviewed boolean not null default false,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index content_chunks_concept_idx on content_chunks (concept_id, "order");
create index content_chunks_subject_idx on content_chunks (subject_id);
create index content_chunks_embedding_idx on content_chunks using hnsw (embedding vector_cosine_ops);

create table questions (
  id text primary key,
  concept_id text not null references concepts (id) on delete cascade,
  subject_id text not null references subjects (id) on delete cascade,
  type question_type not null,
  difficulty smallint not null check (difficulty between 1 and 3),
  prompt text not null,
  code text,
  options jsonb,
  answer jsonb not null,
  explanation text,
  rubric jsonb,
  misconception_tag text,
  diagnoses_prereq text references concepts (id) on delete set null,
  status text not null default 'active' check (status in ('active', 'inactive', 'draft')),
  source text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);
create index questions_concept_idx on questions (concept_id, status);
create index questions_subject_idx on questions (subject_id);

create trigger profiles_updated_at before update on profiles for each row execute function set_updated_at();
create trigger subjects_updated_at before update on subjects for each row execute function set_updated_at();
create trigger concepts_updated_at before update on concepts for each row execute function set_updated_at();
create trigger content_chunks_updated_at before update on content_chunks for each row execute function set_updated_at();
create trigger questions_updated_at before update on questions for each row execute function set_updated_at();

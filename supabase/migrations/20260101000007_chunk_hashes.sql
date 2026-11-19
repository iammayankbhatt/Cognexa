-- Part 7: change tracking for content chunks.
-- content_hash = sha256(heading + text). embedding_hash = the content_hash that the stored embedding was
-- computed from, so scripts/seed_vectors.py only re-embeds chunks whose text changed.

alter table content_chunks
  add column content_hash text,
  add column embedding_hash text,
  add column embedding_model text;

create index content_chunks_pending_embedding_idx on content_chunks (id)
  where embedding is null or embedding_hash is distinct from content_hash;

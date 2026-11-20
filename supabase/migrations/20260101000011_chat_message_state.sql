-- Phase 6: tutor message state.
-- truncated: the client disconnected mid-answer; the partial answer was saved.
-- superseded_at: a regenerated answer replaced this one (kept for feedback/moderation history,
--   hidden from the thread and from the conversation history sent to the model).
-- reply_to: the user message an assistant message answers (regenerate finds the question).
alter table chat_messages
  add column truncated boolean not null default false,
  add column superseded_at timestamptz,
  add column reply_to uuid references chat_messages (id) on delete set null;

create index chat_messages_reply_to_idx on chat_messages (reply_to);

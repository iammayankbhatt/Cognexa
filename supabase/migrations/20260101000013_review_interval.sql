-- Phase 9: spaced review (SM-2-lite ladder 1 -> 3 -> 7 -> 14 -> 30 days). The current interval is
-- stored so the next success moves one step up the ladder; ease already exists on mastery.
alter table mastery
  add column review_interval_days smallint not null default 0
    check (review_interval_days between 0 and 365);

-- Recommendation logging: one row per recommendation shown (rule, reason, path, study group);
-- the surface tells where it was shown (dashboard, tutor, quiz results, review).
alter table recommendations_log
  add column surface text not null default 'dashboard'
    check (surface in ('dashboard', 'tutor', 'quiz', 'review', 'learn'));
create index recommendations_log_open_idx on recommendations_log (user_id, concept_id)
  where completed_at is null;

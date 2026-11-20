-- Phase 12: user-study mode (Objective 5: adaptive vs non-adaptive).

-- Posttest unlock (admin date and/or N days after enrolment), pretest length, and a per-deployment
-- salt for anonymised participant ids in the CSV export.
alter table study_settings
  add column posttest_unlock_at timestamptz,
  add column posttest_after_days smallint not null default 14
    check (posttest_after_days between 0 and 365),
  add column pretest_minutes smallint not null default 20 check (pretest_minutes between 5 and 120),
  add column export_salt text not null default md5(random()::text || clock_timestamp()::text);

-- Enrolment state per participant.
alter table profiles
  add column study_enrolled_at timestamptz,
  add column study_consent_at timestamptz,
  add column study_withdrawn_at timestamptz;

-- Students must not edit their own study state either (only the backend may).
create or replace function prevent_profile_privilege_change() returns trigger
language plpgsql as $$
begin
  if current_user in ('authenticated', 'anon') then
    if new.role is distinct from old.role
       or new.quota_override is distinct from old.quota_override
       or new.study_group is distinct from old.study_group
       or new.study_enrolled_at is distinct from old.study_enrolled_at
       or new.study_consent_at is distinct from old.study_consent_at
       or new.study_withdrawn_at is distinct from old.study_withdrawn_at then
      raise exception 'role, quota and study fields can only be changed by the backend'
        using errcode = '42501';
    end if;
  end if;
  return new;
end;
$$;

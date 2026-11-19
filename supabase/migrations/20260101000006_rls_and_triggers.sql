-- Part 6: row level security, grants and the new-user profile trigger.
-- The backend uses the service role, which bypasses RLS. Browser clients (Supabase anon key + user JWT) get only
-- what is granted here: read their own rows, plus a few self-service writes. anon gets nothing.

-- ---------------------------------------------------------------- enable RLS on every table
alter table profiles enable row level security;
alter table subjects enable row level security;
alter table concepts enable row level security;
alter table content_chunks enable row level security;
alter table questions enable row level security;
alter table quiz_sessions enable row level security;
alter table quiz_answers enable row level security;
alter table mastery enable row level security;
alter table notes enable row level security;
alter table revision_sheets enable row level security;
alter table recommendations_log enable row level security;
alter table chat_threads enable row level security;
alter table chat_messages enable row level security;
alter table message_feedback enable row level security;
alter table usage_daily enable row level security;
alter table global_usage_daily enable row level security;
alter table response_cache enable row level security;
alter table graph_proposals enable row level security;
alter table study_settings enable row level security;
alter table eval_runs enable row level security;
alter table eval_results enable row level security;
alter table app_settings enable row level security;
alter table audit_log enable row level security;

-- ---------------------------------------------------------------- grants (defence in depth)
revoke all on all tables in schema public from anon;
revoke all on all sequences in schema public from anon;
-- Backend-only tables: nothing for browser roles, even if a policy were added by mistake.
revoke all on content_chunks, questions, response_cache, global_usage_daily, graph_proposals,
  study_settings, eval_runs, eval_results, app_settings, audit_log from authenticated;

-- ---------------------------------------------------------------- policies for signed-in users
create policy profiles_select_own on profiles for select to authenticated
  using (id = (select auth.uid()));
create policy profiles_update_own on profiles for update to authenticated
  using (id = (select auth.uid())) with check (id = (select auth.uid()));

create policy subjects_read on subjects for select to authenticated using (true);
create policy concepts_read on concepts for select to authenticated using (true);

create policy quiz_sessions_select_own on quiz_sessions for select to authenticated
  using (user_id = (select auth.uid()));
create policy quiz_answers_select_own on quiz_answers for select to authenticated
  using (user_id = (select auth.uid()));
create policy mastery_select_own on mastery for select to authenticated
  using (user_id = (select auth.uid()));
create policy revision_sheets_select_own on revision_sheets for select to authenticated
  using (user_id = (select auth.uid()));
create policy recommendations_select_own on recommendations_log for select to authenticated
  using (user_id = (select auth.uid()));
create policy usage_daily_select_own on usage_daily for select to authenticated
  using (user_id = (select auth.uid()));
create policy chat_messages_select_own on chat_messages for select to authenticated
  using (user_id = (select auth.uid()));

create policy notes_select_own on notes for select to authenticated
  using (user_id = (select auth.uid()));
create policy notes_insert_own on notes for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy notes_update_own on notes for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy notes_delete_own on notes for delete to authenticated
  using (user_id = (select auth.uid()));

create policy chat_threads_select_own on chat_threads for select to authenticated
  using (user_id = (select auth.uid()));
create policy chat_threads_insert_own on chat_threads for insert to authenticated
  with check (user_id = (select auth.uid()));
create policy chat_threads_update_own on chat_threads for update to authenticated
  using (user_id = (select auth.uid())) with check (user_id = (select auth.uid()));
create policy chat_threads_delete_own on chat_threads for delete to authenticated
  using (user_id = (select auth.uid()));

create policy message_feedback_select_own on message_feedback for select to authenticated
  using (user_id = (select auth.uid()));
create policy message_feedback_insert_own on message_feedback for insert to authenticated
  with check (user_id = (select auth.uid()));

-- ---------------------------------------------------------------- privilege-escalation guard
-- A signed-in user may edit their own profile (name, theme, onboarding flag) but never their role,
-- quota override or study group; only the backend (service role / table owner) may change those.
create or replace function prevent_profile_privilege_change() returns trigger
language plpgsql as $$
begin
  if current_user in ('authenticated', 'anon') then
    if new.role is distinct from old.role
       or new.quota_override is distinct from old.quota_override
       or new.study_group is distinct from old.study_group then
      raise exception 'role, quota and study group can only be changed by the backend'
        using errcode = '42501';
    end if;
  end if;
  return new;
end;
$$;
create trigger profiles_guard_privileges before update on profiles
  for each row execute function prevent_profile_privilege_change();

-- ---------------------------------------------------------------- profile row for every new auth user
create or replace function handle_new_user() returns trigger
language plpgsql security definer set search_path = public as $$
begin
  insert into public.profiles (id, display_name)
  values (
    new.id,
    coalesce(
      nullif(new.raw_user_meta_data ->> 'full_name', ''),
      nullif(new.raw_user_meta_data ->> 'name', ''),
      nullif(split_part(coalesce(new.email, ''), '@', 1), '')
    )
  )
  on conflict (id) do nothing;
  return new;
end;
$$;
revoke all on function handle_new_user() from public, anon, authenticated;

create trigger on_auth_user_created after insert on auth.users
  for each row execute function public.handle_new_user();

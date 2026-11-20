# Cognexa — Deployment runbook (free tiers)

Exact, numbered steps to put Cognexa in production and keep it there. No screenshots: menu paths
are written as **Dashboard → Menu → Item**. Account creation is in
[PHASE0_SETUP.md](PHASE0_SETUP.md); this runbook assumes those accounts exist.

```
Browser ──► Vercel (apps/web, Next.js) ──► Render free web service (apps/api, Docker)
                │ Supabase Auth (JWT)            ├──► Supabase Postgres  (cognexa-prod, pooler :6543)
                ▼                                ├──► Neo4j AuraDB Free  (concept graph + chunks)
            Supabase cognexa-prod                └──► Groq (primary LLM) / Gemini (fallback, judge, embeddings)
GitHub Actions: CI on every push (Render deploys only after it is green) + daily keep-alive ping
```

**Golden rules.** Never paste a secret into chat, an issue or a commit. Production secrets live
only in the password manager, the Render / Vercel / GitHub dashboards and, while seeding, in
`apps/api/.env.production` on your laptop (gitignored by `.env.*`; delete it when done). Every
script that writes to a database refuses a non-local host unless you add `--allow-remote`.

---

## 1. What you need before you start

| Item | Where it comes from | Used by |
|---|---|---|
| Supabase `cognexa-prod` project | PHASE0 Step 3 | Auth + Postgres |
| Its **project URL** and **anon / publishable key** | Supabase → Project Settings → API | web, smoke test |
| Its **service-role / secret key** | same page (keep backend-only) | API |
| **Transaction pooler** connection string (port **6543**) | Supabase → Connect → Transaction pooler | API `DATABASE_URL` |
| Neo4j AuraDB Free instance: URI, user, password | PHASE0 Step 5 (the credentials file you downloaded) | API, seeding |
| Groq API key (`cognexa-prod`) | PHASE0 Step 6 | API |
| Gemini API key | PHASE0 Step 7 | API (fallback, judge, embeddings) |
| Current model ids | Groq console → Models; Google AI Studio → model list | API (never hardcoded) |
| Custom SMTP configured | PHASE0 Step 10 | real users' e-mails |
| Supabase CLI | `npx supabase --version` (already used locally) | migrations |

## 2. Environment variables

### 2.1 API (Render service `cognexa-api`)

`render.yaml` declares all of them. Fixed values are set by the Blueprint; the ones marked
**ask** are prompted once when the Blueprint is created (`sync: false`).

| Variable | Value | Source |
|---|---|---|
| `APP_ENV` | `production` | Blueprint |
| `LOG_LEVEL` | `INFO` | Blueprint |
| `DEFAULT_SUBJECT_ID` | `dsa` | Blueprint |
| `EMBEDDING_DIM` | `768` (must equal `vector(768)` in the migrations) | Blueprint |
| `HEALTH_CHECK_TIMEOUT_S` | `5` | Blueprint |
| `LLM_PRIMARY_PROVIDER` / `LLM_FALLBACK_PROVIDER` / `LLM_JUDGE_PROVIDER` / `EMBEDDING_PROVIDER` | `groq` / `gemini` / `gemini` / `gemini` | Blueprint |
| `ALLOWED_ORIGINS` | `https://<your-app>.vercel.app` (comma-separate a custom domain; **no localhost, no `*`**) | ask |
| `DATABASE_URL` | the transaction-pooler string with the scheme changed to `postgresql+asyncpg://` and your DB password filled in, port 6543 | ask |
| `NEO4J_URI` / `NEO4J_USER` / `NEO4J_PASSWORD` | `neo4j+s://<id>.databases.neo4j.io` / `neo4j` / … | ask |
| `SUPABASE_URL` | `https://<project-ref>.supabase.co` (the JWKS URL is derived from it) | ask |
| `SUPABASE_SERVICE_ROLE_KEY` | service-role / secret key | ask |
| `GROQ_API_KEY`, `GEMINI_API_KEY` | keys | ask |
| `LLM_PRIMARY_MODEL` | a current Groq chat model id | ask |
| `LLM_FALLBACK_MODEL`, `LLM_JUDGE_MODEL` | a current Gemini chat model id | ask |
| `EMBEDDING_MODEL` | a current Gemini embedding model that can output 768 dimensions | ask |
| `SUPABASE_JWT_SECRET` | only if the project still signs tokens with the legacy HS256 secret | dashboard, optional |
| `GEMINI_API_VERSION` | `v1beta` only if `llm_smoke.py` reports HTTP 400 on the Gemini JSON check | dashboard, optional |

The API logs one `production config: ...` warning per missing or suspicious setting at start-up
(Render → cognexa-api → Logs). A correct configuration logs none. Pooler note: the code already
disables prepared-statement caches (CLAUDE.md rule 6); always use port **6543** for the API.

### 2.2 Web (Vercel project, Production environment only)

| Variable | Value |
|---|---|
| `NEXT_PUBLIC_API_URL` | `https://cognexa-api.onrender.com` (your Render URL, no trailing slash) |
| `NEXT_PUBLIC_SUPABASE_URL` | `https://<project-ref>.supabase.co` |
| `NEXT_PUBLIC_SUPABASE_ANON_KEY` | the anon / publishable key (public by design; RLS protects data) |

Never give the web app the service-role key.

### 2.3 GitHub (repository → Settings → Secrets and variables → Actions)

| Kind | Name | Value |
|---|---|---|
| Variable | `API_URL` | the Render URL; turns on the keep-alive workflow |
| Secrets / variables for the manual evaluation | see progressfile.md Human Action #19 | optional |

## 3. Deploy order (first time)

Order matters: data first, then the API, then the web app (whose URL the API's CORS needs), then
auth redirects.

### 3.1 Production database schema (Supabase `cognexa-prod`)

Use the **Supabase CLI**, not `scripts/migrate.py` (which refuses Supabase databases, BUG-014)
and not the SQL editor (it does not record which migrations ran).

1. `npx supabase login` (opens the browser once).
2. `npx supabase link --project-ref <project-ref>` (the ref is in the project URL). It asks for the
   database password.
3. `npx supabase db push --dry-run` and read the list: it must be exactly the files in
   `supabase/migrations/` (the test-only `supabase/shim/` is never pushed).
4. `npx supabase db push`.
5. Check: Supabase → Table Editor shows `profiles`, `concepts`, `content_chunks`, …;
   Database → Extensions shows `vector` enabled.

### 3.2 Seed production data (from your laptop)

1. Create `apps/api/.env.production` (gitignored) with **only** the production values of
   `DATABASE_URL` (you may use the session pooler, port 5432, for seeding), `NEO4J_URI`,
   `NEO4J_USER`, `NEO4J_PASSWORD`, `EMBEDDING_PROVIDER=gemini`, `EMBEDDING_MODEL`,
   `EMBEDDING_DIM=768`, `GEMINI_API_KEY`.
2. From the repo root, in Git Bash:
   ```bash
   export COGNEXA_ENV_FILE=apps/api/.env.production
   uv run --project apps/api python scripts/check_env.py           # names + SET/MISSING only
   uv run --project apps/api python scripts/validate_graph.py
   uv run --project apps/api python scripts/seed_neo4j.py --allow-remote
   uv run --project apps/api python scripts/seed_postgres.py --allow-remote
   uv run --project apps/api python scripts/seed_vectors.py --allow-remote   # real embeddings; resumable
   unset COGNEXA_ENV_FILE
   ```
   `seed_vectors.py` stops cleanly on free-tier limits; run the same command again later and it
   continues where it stopped (chunks are tracked by content hash).
3. Keep `.env.production` only as long as you need it, or keep it in the password manager instead.

### 3.3 API on Render

1. Render → **New → Blueprint** → connect the GitHub repo → it finds `render.yaml`.
2. Fill in every **ask** variable from §2.1. Leave `ALLOWED_ORIGINS` as
   `https://placeholder.invalid` for now if you do not know the Vercel URL yet (step 3.5 fixes it).
3. **Apply.** The first build takes a few minutes. When it is live, open
   `https://<render-url>/health` → `{"status":"ok"}` and `/health/deep` → both dependencies `ok`.
4. Render → cognexa-api → Logs: read the `production config:` warnings, if any, and fix them in
   Render → cognexa-api → Environment (saving redeploys).
5. Deploys: `autoDeployTrigger: checksPass` means Render deploys a push to `main` only after the
   GitHub CI checks are green. A red CI never reaches production.

### 3.4 Web on Vercel

1. Vercel → **Add New → Project** → import the GitHub repo.
2. **Root Directory: `apps/web`** (framework preset Next.js is detected; leave build settings
   default).
3. Environment Variables (Production): the three from §2.2.
4. **Deploy.** Note the production URL, e.g. `https://cognexa.vercel.app`.
5. **Preview deployments are disabled on purpose** (decision DEC-054): `apps/web/vercel.json`
   enables Git deployments for `main` only. Previews would need their own CORS origin and would
   talk to the production API and database. To try a change, run it locally against the dev
   stack. Check after the first deploy: Vercel → Project → Settings → Git shows the setting, and
   a push to another branch creates no deployment. If a non-`main` deployment appears anyway, add
   a fallback in Settings → Build and Deployment → **Ignored Build Step** (exit code 0 skips the
   build, 1 builds): `if [ "$VERCEL_GIT_COMMIT_REF" = "main" ]; then exit 1; else exit 0; fi`.

### 3.5 Connect them (CORS)

1. Render → cognexa-api → Environment → `ALLOWED_ORIGINS` = the Vercel production URL (add a
   custom domain comma-separated if you have one). Save (redeploys).
2. Local development keeps `http://localhost:3000` in `apps/api/.env` only. Production must not
   list localhost; the start-up audit warns if it does.

### 3.6 Supabase Auth for production

Supabase → `cognexa-prod`:

1. **Authentication → URL Configuration:** Site URL = `https://<vercel-url>`. Redirect URLs:
   `https://<vercel-url>/auth/callback` (add the custom domain's callback too). Do not add
   localhost to the production project.
2. **Authentication → Sign In / Providers → Google:** enabled with the Google OAuth client.
   In Google Cloud Console → APIs & Services → Credentials → your OAuth client: Authorized
   JavaScript origins add `https://<vercel-url>`; Authorized redirect URIs must contain
   `https://<project-ref>.supabase.co/auth/v1/callback`.
3. **Authentication → SMTP Settings:** confirm custom SMTP is on (PHASE0 Step 10). Without it
   other people get no confirmation or reset e-mails and the templates cannot be edited.
4. **Authentication → Email Templates:** brand "Confirm signup" and "Reset password":
   subject `Confirm your Cognexa account` / `Reset your Cognexa password`; body starts
   `Welcome to Cognexa, the DSA tutor that explains the "why".` and keeps the
   `{{ .ConfirmationURL }}` link. Sender name: `Cognexa`.

### 3.7 First admin

1. Sign up on the live site with your own address and confirm the e-mail.
2. With `COGNEXA_ENV_FILE=apps/api/.env.production` set as in §3.2:
   `uv run --project apps/api python scripts/promote_admin.py <your e-mail> --allow-remote`
   (idempotent, written to `audit_log`; `--role student` demotes).
3. Wait 30 s (role cache), reload: the **Admin** link appears. Further roles are given in
   Admin → Users.

### 3.8 Keep-alive

1. GitHub → Settings → Secrets and variables → Actions → Variables → `API_URL` = the Render URL.
2. Actions → **Keep-alive** → Run workflow once; it must be green. It then runs daily at
   06:17 UTC, waking the API and querying Postgres **and** Neo4j so Aura Free (pauses after about
   72 h idle) and Supabase Free (pauses after about a week idle) stay active. A failure e-mails the
   repository owner.
3. GitHub disables scheduled workflows after **60 days without repository activity**. If the
   workflow shows "disabled", press **Enable workflow** (or push a commit).

## 4. Verify (production smoke test)

Automated half, from the repo root (use a confirmed **test** account, not your admin):

```bash
export SUPABASE_URL=https://<project-ref>.supabase.co SUPABASE_ANON_KEY=<anon key>
export SMOKE_EMAIL=<test account> SMOKE_PASSWORD=<its password>
uv run --project apps/api python scripts/prod_smoke.py \
  --api https://<render-url> --web https://<vercel-url> --report smoke.md
```

It checks: API awake, deep health (Postgres + Neo4j), CORS (web origin allowed, foreign origin
rejected), protected routes answer 401 with the error envelope, concept graph seeded, landing
page, sign-in, `/me`, the canonical recursion question brings `call_stack` into the trace, the
quota meter goes up by one, recommendations and knowledge map load. Exit code 0 = all passed.
Paste the table into progressfile.md (Phase 15 session log).

Manual half (tick each in progressfile.md):

- [ ] Sign up with a real e-mail → confirmation e-mail arrives (branded) → sign in → onboarding.
- [ ] Forgot password → reset e-mail → new password works.
- [ ] Continue with Google → lands in the app; a `profiles` row exists.
- [ ] Tutor: ask *"Why does my recursive function crash for big inputs with maximum recursion
      depth exceeded?"* → the answer cites Call Stack; the Why panel shows the prerequisite path.
- [ ] Take a concept quiz, answer some wrong → results show mastery change.
- [ ] Dashboard: Next best step points at a weak prerequisite.
- [ ] Knowledge Map renders with mastery colours.
- [ ] Report an answer (flag icon) → as admin, the report is visible.
- [ ] Usage meter in the top bar went up after the tutor question.
- [ ] Switch theme to Titanium Light (projector) and back.
- [ ] Lighthouse (mobile) on the landing page: target 90+ (LIM-015).

## 5. Roll back

- **API:** Render → cognexa-api → Events → pick the last good deploy → **Rollback**. Then fix
  forward on `main` (a revert commit), since the next green push redeploys.
- **Web:** Vercel → Project → Deployments → last good production deployment → **⋯ → Promote to
  Production** (instant rollback).
- **Database:** migrations are forward-only. Write a new migration that undoes the change and
  `supabase db push` it. Before risky migrations take a backup: Supabase → Database → Backups
  (free plan: daily backups, restore via support) or `npx supabase db dump -f backup.sql` from
  the linked project.

## 6. Re-seed Neo4j (Aura deleted or reset the instance)

Aura Free pauses after about 72 h idle and **deletes** instances paused for too long. The graph
is fully reproducible from git:

1. Aura console → create a new AuraDB Free instance (save the new credentials file).
2. Update `NEO4J_URI` / `NEO4J_PASSWORD` in `apps/api/.env.production` and in Render →
   Environment (saving redeploys).
3. `COGNEXA_ENV_FILE=apps/api/.env.production uv run --project apps/api python scripts/seed_neo4j.py --allow-remote`
   (concepts, edges and content chunks).
4. Edges approved in the admin editor since the last commit exist only in the old instance.
   Export them before deleting when possible; otherwise re-approve. Keep `concepts.yaml` as the
   source of truth by copying accepted edges into it.
5. `/health/deep` → neo4j `ok`; run the smoke test.

## 7. Rotate keys

Rotate immediately if a key may have leaked (pasted somewhere, committed, shared screen).

| Key | Rotate at | Then update |
|---|---|---|
| Groq | Groq console → API Keys → delete + create | Render `GROQ_API_KEY` |
| Gemini | AI Studio → API keys → delete + create | Render `GEMINI_API_KEY`, GitHub secret |
| Supabase service-role / secret key | Project Settings → API Keys → create a new secret key, then revoke the old one | Render `SUPABASE_SERVICE_ROLE_KEY` |
| Supabase anon / publishable key | same page (new publishable key) | Vercel `NEXT_PUBLIC_SUPABASE_ANON_KEY`, redeploy |
| Supabase JWT signing key | Project Settings → JWT Keys → rotate (standby key first) | nothing: the API refreshes the JWKS within 10 minutes |
| Database password | Database → Settings → Reset password | Render `DATABASE_URL` |
| Neo4j password | Aura → instance → Reset password | Render `NEO4J_PASSWORD` |

If a secret was committed: rotate it first, then remove it from history only with the human's
explicit approval (rewriting history needs a force-push, CLAUDE.md rule 10).

## 8. Free-tier limits and what happens when they are hit

| Service | Limit (free) | What users see | What to do |
|---|---|---|---|
| Render web service | 512 MB RAM, 0.1 CPU, sleeps after 15 min idle (about 1 min to wake), 750 instance-hours/month, may restart at any time | First request after idle is slow; the web app shows "waking up the server" | Warm it 2 minutes before a demo (open `/health`). One instance only: in-memory rate limits and caches reset on restart |
| Vercel Hobby | non-commercial use, generous bandwidth | nothing normally | keep it a student project |
| Supabase Free | 500 MB database, 50k monthly active users, pauses after about 1 week idle, 2 free projects | paused project = API `/health/deep` shows postgres `error`, sign-in fails | keep-alive prevents the pause; if paused, Supabase → Restore project |
| Supabase built-in e-mail | only to team addresses, a few per hour | sign-up e-mail never arrives | custom SMTP (PHASE0 Step 10) |
| Neo4j AuraDB Free | 200k nodes / 400k relationships, pauses after about 72 h idle, deleted if paused too long | tutor and graph pages fail; `/health/deep` neo4j `error` | keep-alive; resume in the Aura console; §6 if deleted |
| Groq free | per-model requests and tokens per minute and per day | after retries the router falls back to Gemini | nothing; the router handles it |
| Gemini free | per-model requests per minute / per day | if both providers are limited: "The AI service is not responding right now" | Cognexa's own quotas (Admin → Settings: global daily cap, per-user quota) keep usage under the provider limits; lower them if this happens |
| GitHub Actions | free for public repos; scheduled workflows disabled after 60 days of inactivity | keep-alive stops → services pause | §3.8 step 3 |

## 9. Local container check (before changing the Dockerfile)

```bash
docker build -f apps/api/Dockerfile -t cognexa-api:local .
docker run --rm -p 8010:9000 -e PORT=9000 --network cognexa_default \
  -e DATABASE_URL=postgresql+asyncpg://cognexa:cognexa_dev_password@postgres:5432/cognexa \
  -e NEO4J_URI=bolt://neo4j:7687 -e NEO4J_USER=neo4j -e NEO4J_PASSWORD=cognexa_dev_password \
  -e ALLOWED_ORIGINS=http://localhost:3000 cognexa-api:local
curl localhost:8010/health/deep
```

CI (`container` job) builds the same image on every push and checks that it boots on a custom
`$PORT`, answers `/health`, runs as a non-root user and contains `data/subjects`.

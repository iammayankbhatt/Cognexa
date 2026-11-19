# Cognexa — Progress File

> The single source of truth for **what has been built, how, with what, what broke, and how it was fixed**.
> Claude Code updates this at the end of every session (CLAUDE.md §9). The team reads it to study the project and to write the final report.
> Rule: **never delete history.** Mark things superseded instead.

---

## Autopilot State

> Maintained by Claude Code in autopilot mode (user prompt of 2026-11-19). Read this first when resuming. Uncommitted work is normal: one commit per phase.

**Mode:** autopilot, main only, no tags. One commit per phase (`feat(phase-NN): ...`), then `git push origin main` (explicitly authorised for autopilot; if push fails, log it under Human Action Needed and continue). No `gh` CLI and no Supabase CLI were found on this machine at start; CI runs are checked through the public GitHub API when possible.
**Environment notes:** local `apps/api/.env` and `apps/web/.env.local` exist (created from the examples; fake LLM/embedding providers, `REPLACE_ME` for cloud values). Never open or print them; use `uv run --project apps/api python scripts/check_env.py`.
**Phase order:** core 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9 → 10 → 12 → 15 (prep only), then extras 11 → 13 → 14 → 16.
**Current phase:** 5 — LLM layer, quotas, cost, cache, guardrails (not started). Phase 4 complete (Session 8): auth, roles, app shell, public pages.

**Phase 2 checkpoints (done)**
- [x] 2.1 Env files, `scripts/check_env.py`, `.env.example` for all phases
- [x] 2.2 `concepts.yaml` (69 concepts, 111 prerequisite + 20 related edges)
- [x] 2.3 `scripts/validate_graph.py` + `assign_order_index.py` + unit tests (cyclic fixture)
- [x] 2.4 Neo4j schema, `GraphRepository`, `seed_neo4j.py`, 19 integration tests
- [x] 2.5 SQL migrations (6 files), auth shim for plain Postgres, `scripts/migrate.py`, 17 migration/RLS tests
- [x] 2.6 `app/db` (engine, Core tables, repositories), `seed_postgres.py`, 6 seed tests
- [x] 2.7 CI updated, full verification, wrap-up

**Phase 3 checkpoints**
- [x] 3.1 Content tooling: `validate_content.py`, snippet runner, content/question schemas + tests
- [x] 3.2 Cluster: foundations (11 concepts)
- [x] 3.3 Cluster: complexity (5)
- [x] 3.4 Cluster: linear (9)
- [x] 3.5 Cluster: searching_hashing (8)
- [x] 3.6 Cluster: sorting (7)
- [x] 3.7 Cluster: trees (13), commit `a966916`
- [x] 3.8 Cluster: graphs (10) `4d5d964` and paradigms (6) `0fb67d4`
- [x] 3.9 Eval test set (85 items) + study sets, CI `--strict`, seeds re-run, spot-check, wrap-up

**Phase 4 checkpoints (done)**
- [x] 4.1 Supabase local stack runs (CLI 3.2.0 via npx; auth/kong/rest/db/mailpit only). All 9 migrations apply on Supabase Postgres 17. Dev API uses it (`DATABASE_URL` → 127.0.0.1:54322); tests use `TEST_DATABASE_URL` (docker pgvector). ES256 signing key in gitignored `supabase/signing_keys.json`
- [x] 4.2 Backend auth: `app/auth/` (JWKS cache, ES256/RS256 + optional HS256, role from profiles with TTL cache), `/me` GET/PATCH, onboarding, export, DELETE `/me` (Supabase admin API or SQL fallback), `/admin/users` list/search/patch + audit_log; 22 new tests; live cycle verified against the local stack
- [x] 4.3 Web auth written: `@supabase/ssr` 0.12.7 clients, `src/proxy.ts` (Next 16 proxy: session refresh via `getClaims`, redirects for /app and /admin), sign-up / sign-in / forgot / reset pages, `/auth/callback`, Google button, typed API client (token, one 401 retry, error envelope, cold-start signal). Unit tests: 30 new
- [x] 4.4 App shell written: sidebar (collapsible, mobile drawer), top bar (concept search via new `GET /concepts`, usage meter, user menu), theme sync to profile, onboarding flow (diagnostic step is a clearly marked placeholder for Phase 8), dashboard, settings, admin gate + `/admin/users`; placeholder pages for Tutor, Learn, Quizzes, Review, Notes (marked with their phase)
- [x] 4.5 Public pages written: landing (animated graph background, failure-case animation, pipeline, features, comparison), `/how-it-works` (live graph from new public `GET /graph`), About, Privacy, Terms
- [x] 4.6 Settings: data export (JSON download) and account deletion (typed confirmation; backend deletes the auth user via the Auth admin API)
- [x] 4.7 Verified: backend 161 tests, frontend 103 unit + 24 e2e (incl. 6 live auth tests against the local Supabase stack, twice from a cold dev server), screenshots in `docs/screenshots/phase4/`, Lighthouse (desktop 100/100/100/100; mobile perf 74-80, see LIM-015); BUG-015 to BUG-017 fixed; committed as `feat(phase-04)`

**Next action:** start Phase 5: split it into checkpoints from docs/COGNEXA_PROMPTS.md (provider layer with fake/Groq/Gemini, retries + fallback + metering, usage guard, caches, guardrails).
**Local stack:** `npx supabase start -x realtime,storage-api,imgproxy,studio,edge-runtime,logflare,vector,supavisor,postgres-meta` (mail UI http://127.0.0.1:54324); schema changes: `npx supabase migration up` (local Supabase) and `DATABASE_URL=<docker url> uv run ... scripts/migrate.py` (docker test DB)

**Last cluster note:** Phase 3 content complete; 69/69 concepts
**Blockers:** none. (The Docker Desktop outage of Session 7 ended after disk space was freed and Docker was relaunched; see Human Action Needed #6.)
**Human Action Needed:** see the table below (grows as phases complete)

| # | Group | Item | Exact steps |
|---|---|---|---|
| 1 | dashboards | Watch CI after each push | `gh` is not installed. After each autopilot push, open GitHub → Actions and confirm the run is green (or install GitHub CLI and run `gh auth login`). Red CI: tell Claude Code to fix it first. |
| 2 | live checks | ~~Supabase local stack not yet tried~~ **Done locally (Phase 4):** real email sign-up, confirmation mail, sign-in and sign-out are covered by `e2e/auth.spec.ts` on the local stack. Still to do on your **cloud** Supabase project: sign up with your own address, confirm the email, sign in, reset the password. | After the Phase 15 deploy, run those steps on the live site. Built-in Supabase email only reaches your own addresses until custom SMTP is set up (item 9). |
| 3 | content to review | Phase 2 graph edges | Review `data/subjects/dsa/concepts.yaml` (prerequisite edges, aliases, keywords, difficulty). Appendix C is a draft, not gospel. Flip nothing automatically: edge changes are made in the file, then `scripts/validate_graph.py` and `scripts/seed_neo4j.py --prune`. |
| 4 | content to review | Phase 3 notes and questions (all 69 concepts, 552 questions), study sets and the 85-item eval set (`data/subjects/dsa/eval/testset.jsonl`, especially the 27 `unnamed_prerequisite` items, which carry the project's central claim) | Read the notes and questions in `data/subjects/dsa/` (start with the concepts you know best). The checklist is in progressfile.md section 12. When a concept is correct, tick it there and set `reviewed: true` in the note's frontmatter, then re-run `scripts/seed_postgres.py` and `scripts/seed_neo4j.py`. Everything is currently `reviewed: false`. |
| 5 | live checks | Run the real embedding model | `scripts/seed_vectors.py` uses a deterministic fake embedding. After adding `GEMINI_API_KEY` and wiring the real provider (Phase 5), re-run it; chunks are re-embedded because the model name differs. |
| 6 | live checks | ~~Docker engine down (BLOCKER)~~ **Resolved 2026-11-20** (relaunched after disk space was freed: 95% → 68% used). Kept for history. | Docker Desktop stopped mid-session and the engine pipe (`dockerDesktopLinuxEngine`) never came back after two launches (about 25 min). Open Docker Desktop, wait for the whale icon to say "running" (if it shows an error, choose Restart / Troubleshoot, or reboot Windows). Then `docker compose up -d` and `npx supabase start -x realtime,storage-api,imgproxy,studio,edge-runtime,logflare,vector,supavisor,postgres-meta`, start the API (`cd apps/api && uv run uvicorn app.main:app --port 8000`) and tell Claude Code to continue: next action is 4.7 verification. Disk is also 95% full (28 GB free), which can make Docker fail; free some space if it keeps failing. |
| 7 | keys to add | Supabase cloud values for the API and web app | Supabase dashboard → Project Settings → API: project URL into `SUPABASE_URL` (apps/api/.env) and `NEXT_PUBLIC_SUPABASE_URL` (apps/web/.env.local); the publishable/anon key into `NEXT_PUBLIC_SUPABASE_ANON_KEY`; the service-role/secret key into `SUPABASE_SERVICE_ROLE_KEY` (**backend only**). The JWKS URL is derived from the project URL; set `SUPABASE_JWT_SECRET` only if the project still signs with the legacy HS256 secret. Check with `scripts/check_env.py`. |
| 8 | dashboards | Supabase Auth settings + migrations | Authentication → URL Configuration: Site URL = your Vercel URL; Redirect URLs: add `https://<vercel-domain>/auth/callback` and `http://localhost:3000/auth/callback`. Providers → Google: enable it with a Google Cloud OAuth client (authorised redirect URI `https://<project-ref>.supabase.co/auth/v1/callback`). Apply migrations with `supabase db push` (never `scripts/migrate.py`, which refuses Supabase-managed databases, BUG-014). |
| 9 | dashboards | Custom SMTP (optional, for other users) | Built-in Supabase email only reaches organisation members. To let other students sign up, configure custom SMTP (Authentication → SMTP Settings), for example with a free Brevo or Resend account. |
| 10 | live checks | Google sign-in | After item 8: on the live site click "Continue with Google", finish the consent screen, and check that you land on `/app/onboarding` and that a `profiles` row exists. Cannot be tested locally without a Google OAuth client. |
| 11 | live checks | Lighthouse on the deployed landing page | After Phase 15: run Lighthouse (mobile) on the Vercel URL. The local lab score on this laptop was performance 74-80 (desktop 100); target 90+. If it is still below 90 on Vercel, tell Claude Code (LIM-015). |
| 12 | live checks | Make yourself admin | After signing up on the cloud project: Supabase SQL editor → `update public.profiles set role = 'admin' where id = (select id from auth.users where email = '<your email>');` Wait 30 s (role cache) and reload; the Admin link appears. |

---

## 0. Project Snapshot

| Field | Value |
|---|---|
| Product name | **Cognexa** |
| Report title | Towards Agentic GraphRAG: A Knowledge-Graph-Grounded Tutoring System for Adaptive Computer Science Education |
| Team | Ansh Karki (2318402), Mayank Bhatt (2319093), Divyanshi Kaushik (2318770), Harshita Pant (2318850) |
| Guide | Mr. Akash Chauhan, Assistant Professor |
| Institution / ID | Graphic Era Hill University, Dehradun · Team CSE27-125 |
| Subject (v1) | Data Structures & Algorithms (69 concepts, 8 clusters) |
| Repository | https://github.com/iammayankbhatt/Cognexa |
| Live web app | _TBD (Vercel)_ |
| Live API | _TBD (Render)_ |
| Current phase | Phases 1 to 4 complete; next: Phase 5 (LLM layer, quotas, guardrails). Workflow: single developer, `main` only (DEC-013), autopilot (DEC-019) |
| Overall status | 🟡 In progress |

Status legend: 🔴 Not started · 🟡 In progress · 🟢 Done + verified · ⚠️ Done with known issues · ⏸️ Blocked

---

## 1. One-paragraph summary (keep current)

Cognexa is a GraphRAG-based AI tutor for DSA. A student's question is classified to concepts in a Neo4j prerequisite graph. The graph is walked to collect the concept's content plus its (personally weak) prerequisites, and the LLM answers using only that content, citing concepts. The same graph powers a rule-based recommender that walks prerequisite edges backward from weak concepts to the real gap. Around this core is a full product: auth and roles, quiz engine with auto-grading, mastery tracking, progress dashboard, knowledge map, notes and revision sheets, chat history, feedback and reporting, admin console with LLM-proposed and human-approved graph edits, usage limits and cost metering, and an evaluation suite (RAGAs + a user-study mode). Everything runs on free tiers.

---

## 2. Report → Feature Traceability Matrix

Update the **Status** and **Where in code** columns as phases complete. Examiners will ask "where is objective X?". This table answers it.

| # | Report requirement (source) | Cognexa feature | Phase | Status | Where in code / evidence |
|---|---|---|---|---|---|
| O1 | KG of 40–80 core concepts in Neo4j with PREREQUISITE_OF and RELATED_TO (Obj. 1) | 69-concept DSA graph, validator, seed | 2 | 🟢 | `data/subjects/dsa/concepts.yaml`, `scripts/validate_graph.py`, `scripts/seed_neo4j.py`, `apps/api/app/graph/`, `tests/test_graph_*.py` |
| O2a | Question → concept mapping by LLM, zero-shot (Obj. 2, §1.8) | Classifier + hybrid fallback | 6 | 🔴 | |
| O2b | Graph traversal for prerequisite + related content (Obj. 2) | Cypher traversal, personalised ranking | 6 | 🔴 | |
| O2c | LLM generates grounded answer from retrieved context (Obj. 2) | Answer stage + citations + SSE | 6, 7 | 🔴 | |
| O3a | Rule-based recommender: weak concepts → prerequisite to review (Obj. 3) | Rules R1–R5 | 9 | 🔴 | |
| O3b | Uses quiz performance AND questions asked (Abstract) | Mastery + concept_interest signal | 8, 9 | 🔴 | |
| O4 | Functional end-to-end system (Obj. 4) | Full product, deployed | 1–15 | 🔴 | |
| O5a | User study: adaptive vs non-adaptive baseline (Obj. 5) | Study mode, groups, pre/post tests, export | 3, 9, 12 | 🟡 matched pre/post forms ready | `data/subjects/dsa/questions/_study_sets.yaml` |
| O5b | Comparison against plain, non-graph RAG (§1.9) | plain_rag mode + compare view + eval | 3, 6, 12 | 🟡 eval set ready (85 items, 27 unnamed-prerequisite); pgvector chunks seeded (fake embeddings) | `data/subjects/dsa/eval/testset.jsonl`, `scripts/seed_vectors.py` |
| O5c | RAGAs reference-free metrics (§2.2 [10]) | ragas_eval.py + admin eval page | 12 | 🔴 | |
| G1 | LLM proposes tags, human verifies against fixed schema (Gap I, §3.4) | Proposals pipeline + review queue + PDF ingestion | 11 | 🔴 | |
| G2 | Prerequisites retrieved via explicit Cypher traversal (Gap II) | Traversal stage + "Why this answer?" panel | 6, 7 | 🔴 | |
| G3 | One graph powers both tutor and recommender (Gap III) | Shared GraphRepository | 6, 9 | 🔴 | |
| T | "Agentic" (title) | Bounded agentic controller (answer / diagnostic check / expand) | 6 | 🔴 | |
| X | Explainability: show the edge responsible for a retrieval (§2.3) | Trace + mini-graph in UI | 7 | 🔴 | |
| F | Future scope designed for: multi-subject, ML mastery, diagram parsing (§1.7) | subject_id everywhere, ADDING_A_SUBJECT.md | 2, 16 | 🟡 schema + seeds are subject-agnostic; guide in Phase 16 | `supabase/migrations/*`, `app/graph/loader.py` (`data/subjects/<id>/`), `scripts/seed_*.py --subject` |

### Product features (beyond the report)

| Feature | Phase | Status | Where in code |
|---|---|---|---|
| Email/password + Google login, verification, reset, roles (student/reviewer/admin) | 4 | 🟢 locally (Google: live check pending) | `apps/api/app/auth/`, `apps/api/app/api/me.py`, `apps/web/src/proxy.ts`, `src/components/auth/`, `src/app/(auth)/`, `src/app/auth/callback/`, `e2e/auth.spec.ts`, `tests/test_auth_*.py` |
| Three themes (Neon Noir, Titanium Dark, Titanium Light) | 1, 4 | 🟢 incl. profile sync (`components/app/theme-sync.tsx`, e2e "theme follows the user") | `apps/web/src/app/globals.css`, `src/components/theme/`, `/design` route, `docs/screenshots/phase1/` |
| Landing, How-it-works, About, Privacy, Terms pages | 4 | 🟢 | `src/app/(marketing)/`, `src/components/marketing/`, public `GET /graph` (`app/api/graph.py`), `docs/screenshots/phase4/` |
| Onboarding + diagnostic quiz | 4, 8 | 🟡 onboarding flow done; the diagnostic step is a marked placeholder until Phase 8 | `src/app/app/onboarding/`, `POST /me/onboarding-complete` |
| LLM provider layer with fallback, retries, circuit breaker | 5 | 🔴 | |
| Per-user quotas, rate limits, global cap, cost metering | 5 | 🔴 | |
| Response / classification / embedding caching | 5 | 🔴 | |
| Prompt-injection guardrails, off-topic handling | 5, 6, 13 | 🔴 | |
| Chat history (threads: search, rename, archive, delete) | 7 | 🔴 | |
| Streaming answers, citations, follow-ups, regenerate | 7 | 🔴 | |
| Thumbs up/down + report bad answer → moderation | 7, 11 | 🔴 | |
| Quiz engine (6 modes, 5 question types), auto-grading, LLM short-answer grading | 8 | 🔴 | |
| Mastery model with decay; spaced review (SM-2 lite) | 8, 9 | 🔴 | |
| Concept library + concept pages | 8 | 🔴 | |
| Progress dashboard + Knowledge Map (mastery-coloured DAG) | 10 | 🔴 | |
| Notes, bookmarks, personalised revision sheets (MD/PDF export) | 10 | 🔴 | |
| Admin: graph editor, content/question editor, moderation, users, usage, settings | 4, 11 | 🟡 users page (role, study group, quota override, audit log) done in Phase 4 | `app/api/admin_users.py`, `src/app/admin/users/` |
| Data export + account deletion | 4 | 🟢 | `GET /me/export`, `DELETE /me` (`app/api/me.py`, `app/auth/admin.py`), settings page, `tests/test_auth_api.py` |
| Security hardening, a11y, performance, observability, backups | 13 | 🔴 | |
| Free-tier deployment + keep-alive | 15 | 🔴 | |
| Database schema + RLS (23 tables), migrations runnable on Supabase and plain Postgres | 2, 4 | 🟢 locally; all 9 migrations also apply on the Supabase local stack (Postgres 17) | `supabase/migrations/`, `supabase/shim/auth_shim.sql`, `scripts/migrate.py`, `tests/test_db_migrations.py` |

---

## 3. Tech Stack

> Claude Code fills **Version** with the exact installed version, and adds rows for any new dependency with a reason.

| Layer | Technology | Version | Why we chose it | Free-tier limit to watch |
|---|---|---|---|---|
| Frontend framework | Next.js (App Router) + TypeScript | Next.js 16.4.6, React 19.3.0, TypeScript 5.9.3 (Node 22.14.0) | SSR, routing, Vercel-native | Vercel Hobby: personal / non-commercial use |
| Styling / UI | Tailwind CSS + shadcn/ui | Tailwind 4.3.3, shadcn CLI 4.23.0 (base-nova style, @base-ui/react 1.9.0), lucide-react 1.76.0, sonner 2.0.8, clsx 2.1.1, tailwind-merge 3.7.0 | Fast, consistent, themeable via CSS variables | — |
| Data fetching / forms | TanStack Query, react-hook-form, zod | @tanstack/react-query 5.108.0, react-hook-form 7.92.0, zod 4.6.7, @hookform/resolvers 7.0.7 | Caching, validation | — |
| Charts / graph viz | Recharts, Cytoscape.js + dagre | _not installed yet (Phase 10)_ | Themed charts; DAG layout for prerequisite graph | — |
| Backend | FastAPI + Pydantic v2 (Python 3.12, uv) | Python 3.12.1, uv 0.11.28, FastAPI 0.165.0, Pydantic 2.14.3, pydantic-settings 2.16.3, uvicorn 0.54.0, SQLAlchemy 2.1.9 (+greenlet 3.5.6), asyncpg 0.32.0, neo4j driver 6.4.1 | Async, typed, Python AI ecosystem | Render Free: sleeps after 15 min, ~1 min cold start, 512 MB RAM |
| Graph database | Neo4j AuraDB Free (prod) / neo4j:5 Docker (dev, CI) | neo4j:5 image resolved to Neo4j 5.26.33 | Native graph + Cypher, explainable traversal | Pauses after 72 h idle; small node/relationship caps; no backups |
| Relational DB | Supabase Postgres + pgvector | pgvector/pgvector:pg16 gives PostgreSQL 16.16, pgvector 0.8.7 | Auth + Postgres + vectors in one free service | 500 MB DB, pauses after ~7 days idle, 2 free projects |
| Auth | Supabase Auth | | Email, Google OAuth, JWT | 50k MAU |
| LLM (primary) | Groq (OpenAI-compatible) | model: _env_ | Fast, generous free tier, no training on data | Per-model RPM/RPD/TPM (see console) |
| LLM (fallback) + embeddings | Google Gemini API | model: _env_ | Free tier, embeddings | Low free RPD; prompts may be used to improve products |
| Evaluation | RAGAs, scipy, matplotlib | _not installed yet (Phase 12)_ | Reference-free RAG metrics (report [10]) | Uses LLM quota, so run in batches |
| Testing | pytest, Vitest, Playwright, axe | pytest 9.2.0, pytest-asyncio 1.5.0, httpx 0.28.1, ruff 0.17.5, mypy 2.4.1; Vitest 5.1.1, jsdom 29.1.1, Testing Library (react 16.3.3, jest-dom 8.0.0, user-event 14.6.13), Playwright 1.65.1 (Chromium), Prettier 3.10.1; axe not yet | Unit / integration / e2e / a11y | — |
| CI/CD | GitHub Actions, Vercel, Render | ci.yml (actions/checkout@v4, astral-sh/setup-uv@v6, actions/setup-node@v4) + keepalive.yml; not yet run on GitHub | Free automation | Scheduled workflows disabled after 60 days of repo inactivity |
| Data loading | PyYAML (+ types-pyyaml) | PyYAML 6.0.3, types-pyyaml 6.0.12.20261113 | concepts.yaml source of truth | — |
| Vector type | pgvector (Python package) | pgvector 0.5.1 | SQLAlchemy `Vector` column type for `content_chunks.embedding` | — |

---

## 4. Architecture Summary

```
Browser → Next.js (Vercel) ──JWT──► FastAPI (Render) ─► Neo4j Aura (graph + chunks)
              │                          ├─► Supabase Postgres (+pgvector)
              └─ Supabase Auth           └─► LLM layer: Groq → Gemini fallback
GitHub Actions: CI on push · daily keep-alive /health/deep
```

Key flows (details in docs/ARCHITECTURE.md once written):
1. **Tutor:** classify → traverse → gather → (agentic step) → answer (SSE) → store trace.
2. **Quiz:** start → answer → auto-grade → mastery update → recommendations refresh.
3. **Recommender:** weak concepts → backward prerequisite BFS → frontier gap (R1–R5).
4. **Admin:** LLM proposal → human review → graph/content write → cache invalidation.

---

## 5. Phase Tracker

| Phase | Name | Status | Started | Finished | Commit | Verified by (human) | Notes |
|---|---|---|---|---|---|---|---|
| 0 | Manual setup: accounts & keys | 🔴 | | | — | | |
| 1 | Scaffold, design system, CI | ⚠️ | 2026-11-19 | 2026-11-19 | `fb019e9` (PR #1 merge); CI fix `2fabc20` | | Merged. First GitHub CI run failed at typecheck (BUG-005); fix verified in a fresh clone, awaiting a green run on GitHub, then tag v0.1. |
| 2 | Databases + DSA concept graph | 🟢 | 2026-11-19 | 2026-11-19 | `0f2d90d` `feat(phase-02): databases and the DSA concept graph` | | Verified locally (79 tests) and on GitHub Actions (run 44499463362: backend + frontend jobs success). Supabase-specific behaviour (CLI `db push`, real `auth` schema) still untested (LIM-013). |
| 3 | Content, question bank, eval test set | 🟢 | 2026-11-19 | 2026-11-19 | cluster commits (DEC-020) `67fc84b`…`0fb67d4` + `feat(phase-03)` wrap-up | | 69/69 notes, 552 questions, 138 snippets run, 69 code_output keys verified, study sets, 85-item eval set; validate_content `--strict` in CI. Content still `reviewed: false` (human review pending). |
| 4 | Auth, roles, app shell, public pages | 🟢 | 2026-11-19 | 2026-11-20 | `feat(phase-04): auth, roles, app shell, public pages` | | Verified locally: backend 161 tests, web 103 unit + 24 e2e (live auth cycle on the Supabase local stack), build without env vars (CI parity). Google OAuth and cloud Supabase are live checks (Human Action 2, 7-10, 12). |
| 5 | LLM layer, quotas, cost, cache, guardrails | 🔴 | | | | | |
| 6 | GraphRAG + plain RAG + agentic step | 🔴 | | | | | |
| 7 | Tutor chat UI | 🔴 | | | | | |
| 8 | Quiz engine, grading, mastery | 🔴 | | | | | |
| 9 | Recommender, baseline, spaced review | 🔴 | | | | | |
| 10 | Dashboard, knowledge map, notes | 🔴 | | | | | |
| 11 | Admin console + LLM proposals | 🔴 | | | | | |
| 12 | Evaluation + user study | 🔴 | | | | | |
| 13 | Hardening | 🔴 | | | | | |
| 14 | Bug hunt + fresh-eyes review | 🔴 | | | | | |
| 15 | Deployment + keep-alive | 🔴 | | | | | |
| 16 | Docs, diagrams, demo script | 🔴 | | | | | |

### Phase 0 checklist (human)

- [ ] GitHub repo created
- [ ] Supabase `cognexa-dev` created (vector extension, email auth, Google provider)
- [ ] Supabase `cognexa-prod` created (same config)
- [ ] Neo4j AuraDB Free instance created (credentials saved)
- [ ] Groq API key
- [ ] Gemini API key
- [ ] Google OAuth client configured in Supabase
- [ ] Vercel + Render accounts linked to GitHub
- [ ] Docker, Node LTS, Python 3.12, uv, Claude Code installed
- [ ] Custom SMTP for Supabase auth emails (Gmail app password / Resend / Brevo), required before Phase 15 and the user study
- [ ] Secrets worksheet filled in the password manager (docs/PHASE0_SETUP.md Step 12)

---

## 6. Session Log

> One entry per Claude Code session, newest at the bottom. Template:

```
### Session <n> — <YYYY-MM-DD> — Phase <x>: <title>
**Goal:**
**Built:**
- …
**Files touched:** (key files only)
**Commands run & results:** lint ✅ · typecheck ✅ · tests ✅ (N passed) · build ✅ · e2e ✅/n.a.
**Manual verification:** what was clicked/called and the result
**Bugs found this session:** BUG-xxx, BUG-yyy (see Bug Log)
**Decisions:** DEC-xxx
**Human action needed:** (env vars to add, dashboards to configure)
**What we learned:**
- …
**Next step:**
```

### Session 1 — 2026-11-19 — Phase 1: Scaffold, design system, CI
**Goal:** Monorepo layout, FastAPI skeleton, Next.js app, three-theme design system with `/design` reference, docker compose, CI.
**Built:**
- Monorepo layout per CLAUDE.md §4, root `.gitignore`, README.
- `apps/api`: app factory, pydantic-settings, pure-ASGI request-ID middleware, JSON logging with request-ID correlation, `{error:{code,message,request_id}}` handlers (HTTP, validation, unhandled), `/health` and `/health/deep` (Postgres + Neo4j probes; `not_configured` / `error` never crash), ruff + strict mypy + pytest.
- `apps/web`: Next.js 16 App Router + strict TS + Tailwind 4 + shadcn/ui, Prettier, Vitest, Playwright; three themes as CSS variables on `[data-theme]` mapped into Tailwind and shadcn tokens; own ThemeProvider (`useSyncExternalStore`) + no-flash inline script + segmented ThemeSwitcher; Geist + JetBrains Mono via `next/font`; shared primitives (PageHeader, StatCard, EmptyState, ErrorState, LoadingSkeleton, MasteryBadge, ConceptChip); dev-only `/design` (404 in production).
- `docker-compose.yml` (neo4j:5, pgvector pg16, healthchecks, named volumes, ports from `.env`), `ci.yml`, `keepalive.yml`.
**Files touched:** `apps/api/app/**`, `apps/api/tests/**`, `apps/web/src/**`, `apps/web/e2e/**`, `docker-compose.yml`, `.github/workflows/*`, `README.md`, `docs/screenshots/phase1/*`.
**Commands run & results:** ruff ✅ · mypy ✅ (10 files) · pytest ✅ (13 passed with live DBs; 10 passed + 3 skipped without) · eslint ✅ · tsc ✅ · vitest ✅ (54 passed, incl. WCAG AA contrast for all 3 themes) · `next build` ✅ · Playwright e2e ✅ (7 passed) + screenshots ✅ (3 passed) · `docker compose up -d --wait` ✅ both healthy · workflow and compose YAML parse ✅ (PyYAML only; NOT linted with actionlint and NOT executed on GitHub).
**Manual verification:** started uvicorn: `/health` 200; `/health/deep` reported postgres `ok` + neo4j `ok` against the containers (and `not_configured` with no env); unknown route returned the error envelope. `next start` (production build): `/design` returns 404, home returns 200 with no design link. Viewed the `/design` screenshots (Neon Noir and Titanium Light inspected closely; Titanium Dark generated and checked only via tests).
**Bugs found this session:** BUG-001, BUG-002, BUG-003
**Decisions:** DEC-007 to DEC-011
**Human action needed:** review branch `phase/01-scaffold`, push it and open a PR so CI runs (`git push -u origin phase/01-scaffold`); after merge tag with `git tag -a v0.1 -m "Phase 1: Scaffold, design system, CI"`. A native Postgres is running on port 5432 on this machine (left untouched; see BUG-001).
**What we learned:**
- Tests with the DB unconfigured cannot catch connectivity bugs; the live `/health/deep` run did. Hence the env-gated integration tests.
- `create-next-app` and `shadcn init` output must be read, not trusted: shadcn init here wired `cn` to an unvetted npm package.
- With CSS-variable theming, scoping `data-theme` on a wrapper lets one page show all themes at once (used on `/design` and in the switcher swatches) with no hard-coded hex.
- A request-ID middleware written as pure ASGI (not `BaseHTTPMiddleware`) also covers error responses and keeps log correlation via a `ContextVar`.
- Local port clashes (native Postgres on 5432) look like auth failures, so check what owns a port before debugging credentials.
**Next step:** Phase 2: databases + DSA concept graph.

### Session 2 — 2026-11-19 — Phase 1 follow-ups (branch `phase/01-scaffold`)
**Goal:** Close LIM-007 (theme contrast), audit running Docker containers, record a Phase 4 limitation.
**Built:**
- Neon Noir `--surface #17142A`, `--surface-2 #231E38`, `--border #332C4D`; Titanium Light `--accent #5F6670`. CLAUDE.md section 6 table updated to match `globals.css`.
- Contrast tests extended (accent as text on bg/surface/surface-2 in all themes; border vs bg >= 1.3:1; surface and surface-2 vs bg >= 1.08:1).
- BUG-004: `link` variant of Button and Badge switched from `text-primary` to `text-accent`.
- LIM-007 closed (history kept, struck through); LIM-011 added for Phase 4.
**Docker audit (`docker ps -a`):** 3 containers. Ours: `cognexa-postgres-1` (pgvector/pgvector:pg16, healthy) and `cognexa-neo4j-1` (neo4j:5, healthy); neither runs Python or uvicorn, and the compose file has no API service, so nothing to remove. **Not ours:** `store-intelligence-api-1` (image `store-intelligence-api`, Python 3.11.15, `uvicorn app.main:app --host 0.0.0.0 --port 8000 --reload`, bind mounts `D:\store-intelligence-fixed\store-intelligence\{data->/app/data, events, videos}`, compose project `store-intelligence`, state Exited (255)). It matches the pattern asked about but belongs to a different project; I did not touch it. No Cognexa bug logged for it.
**Files touched:** `CLAUDE.md`, `apps/web/src/app/globals.css`, `apps/web/src/components/ui/{button,badge}.tsx`, `apps/web/src/test/contrast.test.ts`, `docs/screenshots/phase1/*`, `progressfile.md`.
**Commands run & results:** ruff ✅ · mypy ✅ · pytest ✅ (13 passed, live DBs) · eslint ✅ · tsc ✅ · vitest ✅ (69 passed) · `next build` ✅ · Playwright ✅ (7 e2e + 3 screenshot runs) · all 9 screenshots regenerated.
**Manual verification:** viewed `design-titanium-dark.png` and `design-neon-noir.png` after the change (panels distinct, tokens as specified). Titanium Light was checked by measurement (accent 5.80:1 on white, 5.32 on bg, 4.86 on surface-2) and was not re-inspected visually after the change. The Link-variant fix was verified by computed contrast and the full-page test run, not by closer inspection of the new screenshot.
**Bugs found this session:** BUG-004
**Decisions:** none new
**Human action needed:** none beyond the Session 1 push/PR steps.
**What we learned:**
- Checking screenshots by eye for the *dark* theme surfaced a contrast failure (primary used as link text) that the token-pair tests could not see, because they only test pairs we list. Component-level text colours need to be in the pair list or reviewed visually.
- Brand colours (purple, red) are fine for fills with white text but not as text on near-black; use accent for link-like text.
**Next step:** Phase 2: databases + DSA concept graph.

### Session 3 — 2026-11-19 — CI fix (BUG-005) and workflow change (DEC-012), on `main`
**Goal:** Make the GitHub frontend job pass; switch the team workflow to direct commits on `main`.
**Built:**
- Local `main` was stale at the first commit while `origin/main` already contained PR #1; ran `git checkout main && git pull --rebase` (fast-forward to `fb019e9`) before starting.
- BUG-005 fix: `typecheck` script is now `next typegen && tsc --noEmit`.
- Workflow docs: CLAUDE.md section 9 step 3 and `docs/COGNEXA_PROMPTS.md` Appendix D rewritten for commits on `main` (Branch column removed from the commit table, per-phase commit lists kept); `docs/PHASE0_SETUP.md` step 5 no longer requires PRs/status checks on `main`.
**Hidden-dependency audit (CI vs local):** deleted `.next` and `next-env.d.ts`, `npm ci` and re-ran everything; then cloned the repo fresh and ran both CI jobs there. Findings: only the route types depended on gitignored files. `uv.lock`, `package-lock.json`, `.python-version`, `components.json`, `.prettierrc.json`, `vitest.setup.ts` are all tracked. Playwright browsers are not used in CI (e2e is local only). The uv cache is only an accelerator (keyed on tracked `uv.lock`). `next/font/google` needs network at build time, which GitHub runners have. Backend integration tests skip without env vars and run in CI via service containers. Not covered locally: Ubuntu-specific behaviour (case-sensitive paths, line endings) and the Neo4j/pgvector service-container healthchecks in the workflow.
**Files touched:** `apps/web/package.json`, `CLAUDE.md`, `docs/COGNEXA_PROMPTS.md`, `docs/PHASE0_SETUP.md`, `progressfile.md`.
**Commands run & results (fresh clone and in place):** backend: ruff ✅ · ruff format ✅ · mypy ✅ · pytest ✅ (10 passed + 3 skipped without DBs; 13 passed with live DBs) · frontend: `npm ci` ✅ · eslint ✅ · typecheck ✅ (after fix; ❌ before) · vitest ✅ (69 passed) · `next build` ✅. Docs-only commit: no code checks needed beyond the above.
**Manual verification:** reproduced the exact CI error locally before fixing; confirmed it is gone after.
**Bugs found this session:** BUG-005
**Decisions:** DEC-012 (requested ID DEC-008 was already used)
**Human action needed:** push `main` and watch the CI run (commands below). If you created a GitHub ruleset requiring PRs/status checks on `main` (old PHASE0 step 5), relax it or direct pushes will be rejected. After CI is green: tag v0.1.
```
git pull --rebase
git push
# watch: GitHub -> Actions (or: gh run watch)
git tag -a v0.1 -m "Phase 1: Scaffold, design system, CI" && git push --tags   # only after CI is green
```
**What we learned:**
- Generated, gitignored files (`.next/types`, `next-env.d.ts`) make local checks lie. A fresh clone is the only honest CI rehearsal.
- When a requested ID is already taken (DEC-008), allocate the next free one and say so; never overwrite history.
- Branch protection that requires PRs or status checks silently contradicts a commit-to-main workflow.
**Next step:** confirm green CI on GitHub, tag v0.1, then Phase 2: databases + DSA concept graph.

### Session 4 — 2026-11-19 — Workflow change to single-developer main-only (DEC-013)
**Goal:** Docs-only: replace the team workflow (DEC-012) with a solo, main-only workflow.
**Built:** CLAUDE.md section 9 step 3; `docs/COGNEXA_PROMPTS.md` "How to use this pack", Phase 3 review note and Appendix D (workflow and rules of thumb; per-phase commit lists untouched); `docs/PHASE0_SETUP.md` step 5 (ruleset optional), Supabase email note, final checklist; progressfile.md (DEC-013, DEC-012 marked superseded, Phase tracker header, content review checklist reviewer).
**Wording that was NOT found:** "don't run two Claude Code sessions on the same phase" appears in none of the docs; "split content clusters among teammates" appears only as "owns the content review commits for their clusters" (Appendix D rules of thumb), which was removed. The `git pull --rebase` steps were in CLAUDE.md section 9 and Appendix D (both replaced by the one-line `git pull` note).
**Left unchanged on purpose (outside the list requested):** `docs/PHASE0_SETUP.md` still describes a shared team Google account, a GitHub organisation with four owners, four laptops and four test users; CLAUDE.md/progressfile.md still carry the project team credits (Team CSE27-125) and "bullets the team can study".
**Files touched:** `CLAUDE.md`, `docs/COGNEXA_PROMPTS.md`, `docs/PHASE0_SETUP.md`, `progressfile.md`.
**Commands run & results:** docs only, no code touched, so no lint/test/build run. Checked by grep that no `git pull --rebase`, branch, PR, teammate-review or "spread commits" wording remains in CLAUDE.md or Appendix D, and that CRLF line endings were preserved.
**Bugs found this session:** none
**Decisions:** DEC-013 (supersedes DEC-012)
**Human action needed:** if you created a GitHub ruleset that requires PRs/status checks, relax it. Push, watch CI, tag v0.1 when green (commands below). Decide whether to also simplify the remaining team-oriented Phase 0 steps.
```
git push
# watch: GitHub -> Actions (or: gh run watch)
git tag -a v0.1 -m "Phase 1: Scaffold, design system, CI" && git push --tags   # only after CI is green
```
**What we learned:**
- A requested edit list can reference wording that is not in the files; verify with grep and report what was and was not found.
- Decisions are superseded, not deleted: DEC-012 stays in the log, marked.
**Next step:** confirm green CI on GitHub, tag v0.1, then Phase 2: databases + DSA concept graph.

### Session 5 — 2026-11-19 — Phase 2: Databases and the DSA concept graph (autopilot)
**Goal:** Concept graph source of truth + validator, Neo4j repository and seed, Postgres migrations with RLS, seeds, tests, CI.
**Built:**
- `concepts.yaml`: 69 concepts / 8 clusters from Appendix C with descriptions, aliases, keywords, difficulty and a computed topological `order_index`.
- `app/graph/`: Pydantic models, loader, validation (duplicates, unknown refs, cycles with path, self refs, orphans, roots, order_index), `GraphRepository` (parameterised Cypher; transactional cycle-safe `upsert_edge`), idempotent `seed_subject`.
- `scripts/`: `validate_graph.py`, `assign_order_index.py`, `seed_neo4j.py` (`--prune`, `--wipe` with typed confirmation, refuses remote without `--allow-remote`), `migrate.py`, `seed_postgres.py`, `check_env.py`.
- `supabase/migrations/` (6 files): 23 tables, enums, RLS on every table, grants, profile trigger, privilege-escalation guard; `supabase/shim/auth_shim.sql` for plain Postgres.
- `app/db/`: pooler-safe engine factory (rule 6; health check now reuses it), migration runner with checksums, SQLAlchemy Core tables (drift-tested against the real schema), repositories (concept mirror, app settings).
- CI: validator step, live-DB pytest, migrate + seed smoke.
**Graph stats (from `validate_graph.py`):** nodes 69 · PREREQUISITE_OF 111 · RELATED_TO 20 (undirected, deduplicated) · max prerequisite depth 10 · roots 2 (discrete_math_basics, variables_memory) · leaves 28 · clusters: foundations 11, complexity 5, linear 9, searching_hashing 8, sorting 7, trees 13, graphs 10, paradigms 6.
**Files touched:** `data/subjects/dsa/concepts.yaml`, `apps/api/app/{graph,db}/**`, `apps/api/app/core/config.py`, `apps/api/app/health_checks.py`, `apps/api/tests/**`, `scripts/*.py`, `supabase/**`, `.github/workflows/ci.yml`, `apps/api/.env.example`, `apps/web/.env.example`, `CLAUDE.md`, `progressfile.md`.
**Commands run & results:** ruff ✅ · ruff format ✅ · mypy ✅ (22 files) · pytest ✅ (79 passed: validator 25, graph repository 19, migrations/RLS 17, seed 6, health 12; live Neo4j 5.26 + Postgres 16/pgvector 0.8.7) · validate_graph ✅ · assign_order_index --check ✅ · seed_neo4j twice ✅ · migrate twice ✅ · seed_postgres twice ✅ · eslint ✅ · tsc ✅ · vitest ✅ (69) · next build ✅.
**Manual verification:** ran each script against the local docker databases (twice each). Verified in tests that `get_dependents('call_stack', 3)` returns `recursion` at depth 1 and `dfs_tree_traversals` at depth 2 (the Verify item expressed as an assertion); did not open Neo4j Browser. All 24 public tables have RLS enabled (query result, including `schema_migrations`).
**Bugs found this session:** BUG-006, BUG-007
**Decisions:** DEC-014 to DEC-019
**Human action needed:** see Autopilot State table (items 1 to 3).
**What we learned:**
- Cypher cannot parameterise variable-length bounds (`*1..N`); clamp an int and format it, never user text.
- Cycle safety belongs inside the write transaction (`upsert_edge`) so the DAG rule (CLAUDE.md rule 3) cannot be bypassed by a caller who forgot to check first.
- RLS needs two layers: no policy means no access, and `revoke` on backend-only tables protects against a policy added by mistake. Test both with `SET ROLE authenticated` plus a JWT claim.
- A throwaway database per test (`CREATE DATABASE`) gives true migration tests without wiping dev data.
- Resolve `.env` relative to the package, not the working directory, or scripts only work from one folder.
**Next step:** Phase 3 (content): tooling first, then cluster by cluster.


### Session 6 — 2026-11-19 — Phase 3: Content (in progress, autopilot)
**Goal:** Learning content for all 69 DSA concepts, the question bank, study sets and the eval test set; content tooling and seeding.
**Built so far:**
- Tooling (commit `efc832a`): note parser (10 required H2 sections become chunks), question / study-set / test-set schemas, `validate_content.py`, snippet runner (Python + C++14) with `code_output` answer-key verification, chunk and question seeding for Neo4j and Postgres, migrations 0007 (chunk hashes) and 0008 (question language), fake deterministic embeddings and resumable `seed_vectors.py`, review checklist generator, a validator rule rejecting unfinished or self-correcting text.
- Content: **40 of 69 concepts** written with 8 questions each (320 questions): foundations (11), complexity (5), linear (9), searching_hashing (8), sorting (7). All Python and C++14 snippets run, and all `code_output` answers match real program output.
**Still to do:** trees (13), graphs (10), paradigms (6), then `_study_sets.yaml` (two matched 20-question forms), `eval/testset.jsonl` (80+ items with the category minimums), switch CI to `validate_content.py --strict`, Phase 3 wrap-up.
**Commands run & results (latest):** ruff ✅ · mypy ✅ · pytest ✅ (full suite 134 passed before the last content clusters; content gates 41 passed after) · validate_content ✅ · all snippets and answer keys ✅ · seeds twice ✅ · CI green on GitHub for the pushes through the searching_hashing cluster (run ids 44503011332 and later); the sorting push was not yet confirmed at the time of writing.
**Bugs found this session:** BUG-008 to BUG-011
**Decisions:** DEC-020 to DEC-022
**Human action needed:** see the Autopilot State table.
**What we learned:**
- Machine-checking authored answer keys is worth the effort: the verifier caught three wrong keys I had written from memory (amortized_analysis-q07, stack-q07, binary_search-q07) and one muddled explanation. Trace code by hand first, and let the runner be the judge.
- Authored text needs the same lint as code: a confused "wait, that window..." sentence reached a note and is now rejected by the validator.
- Tooling layers can corrupt backslashes: `\b` in a regex and `\n` in a string became control characters when written through the shell. Prefer the file-writing tool for code containing backslashes and verify by running.
- Old compilers constrain content: the local MinGW GCC 6.3 only supports C++14, so notes use C++14 (also compiled by a newer GCC in CI).
**Next step:** trees cluster (3.7).

### Session 7 — 2026-11-19 — Phase 3: Content completed (autopilot)
**Goal:** Finish the remaining 29 concepts, the study sets and the eval test set; close Phase 3.
**Built:**
- Notes and 8 questions each for trees (13, `a966916`), graphs (10, `4d5d964`) and paradigms (6, `0fb67d4`). Every note has runnable Python and C++14 code that asserts its own claims, most with randomised brute-force cross-checks (for example Dijkstra against a Bellman-Ford reference, B-tree invariants for t = 2, 3, 5, Kruskal against Prim, LIS and knapsack against exhaustive search).
- `questions/_study_sets.yaml`: pretest_A / posttest_B, 20 concepts each (the core recommender path from call_stack to dijkstra), one auto-graded question per concept per form, matched difficulty (alternating 1 and 2), no shared questions.
- `eval/testset.jsonl`: 85 items: direct 22, unnamed_prerequisite 27, multi_concept 15, misconception 13, off_topic 8 (including one prompt-injection attempt). Every unnamed_prerequisite item describes a symptom, and the validator confirms the prerequisite is a real ancestor and is not named in the question.
- CI now runs `validate_content.py --strict` (requires all 69 concepts, study sets and the category minimums).
**Files touched:** `data/subjects/dsa/content/*.md` (29 new), `data/subjects/dsa/questions/*.yaml` (29 new + `_study_sets.yaml`), `data/subjects/dsa/eval/testset.jsonl`, `.github/workflows/ci.yml`, `progressfile.md`.
**Commands run & results:** validate_content `--strict` ✅ (69/69 notes, 552 questions, study sets ok, 85 testset items, no warnings) · run_content_snippets ✅ (138 of 138 snippets passed, 0 skipped; 69 of 69 code_output answers match real output) · ruff ✅ · ruff format ✅ · mypy ✅ (31 files) · pytest ✅ (135 passed, live Neo4j + Postgres) · migrate ✅ · seed_postgres ×2 ✅ (690 chunks, 552 questions) · seed_neo4j ×2 ✅ (690 chunks, 0 stale) · seed_vectors ×2 ✅ (290 new embedded, then 0 / 690 skipped). Frontend untouched this session, so no frontend checks were run.
**Manual verification (spot-check):** sampled 10 random auto-graded questions with a fixed seed (binary_tree-q01, dp_fundamentals-q02, merge_sort-q06, minimum_spanning_tree-q05, singly_linked_list-q02, binary_heap-q05, dfs-q01, recurrence_relations-q02, red_black_tree-q01, prefix_sums-q03): all answer keys correct. Sampled 5 concepts (red_black_tree, strings, sliding_window, expression_evaluation, amortized_analysis) and re-read their Complexity sections: accurate. Every worked example in the 29 new notes was traced by hand while writing, and the traces were then asserted in code.
**Bugs found this session:** BUG-012, BUG-013
**Decisions:** none new (DEC-020 to DEC-022 applied)
**Human action needed:** Autopilot State items 1 and 4 (CI watch, content review).
**What we learned:**
- Self-checking code in notes pays off again: an over-strict assertion about DFS interval nesting (BUG-012) was caught by the snippet runner, not by reading.
- Validators catch thin authoring: a 7-character `why_wrong` ("It can.") was rejected (BUG-013); short explanations are not useful to students either.
- The "unnamed prerequisite" rule must be checked by machine. It is easy to name the prerequisite by accident (writing "call stack" in a RecursionError question), and the validator rejects it.
- Heredoc Python with backslashes is still fragile (a `split('\\')` in a throwaway script broke); use `os.path` helpers instead of string escapes in shell-embedded code.
**Next step:** Phase 4: auth, roles, app shell, public pages.

### Session 8 — 2026-11-19/20 — Phase 4: Auth, roles, app shell, public pages (autopilot)
**Goal:** Real authentication with roles, the signed-in app shell, settings (export/delete) and the public marketing pages, verified end to end on the Supabase local stack.
**Built:**
- Supabase CLI local stack (CLI 3.2.0 via npx; auth, kong, rest, db, mailpit). All 9 migrations apply to Supabase Postgres 17 (LIM-013 updated). New migration `20260101000009_profile_experience_level.sql`. ES256 signing key in the gitignored `supabase/signing_keys.json`.
- Backend `app/auth/`: JWKS cache (TTL, early refetch on an unknown `kid`), token verification (ES256/RS256/EdDSA via JWKS, HS256 only when a legacy secret is configured; rejects `alg: none`, wrong `aud`/`iss`/role and non-UUID `sub`), roles from `public.profiles` with a 30 s cache, `require_role`. Endpoints: `GET/PATCH /me`, `POST /me/onboarding-complete`, `GET /me/export`, `DELETE /me` (Auth admin API, SQL fallback on plain Postgres), `GET/PATCH /admin/users` with audit log, `GET /concepts`, public `GET /graph` (5-minute cache, approved nodes/edges only). `migrate.py` refuses CLI-managed databases (BUG-014). Tests use `TEST_DATABASE_URL`, so the dev API can point at the Supabase stack.
- Web: `@supabase/ssr` 0.12.7 clients; `src/proxy.ts` (Next 16 proxy: session refresh with `getClaims`, redirects for `/app` and `/admin`, open-redirect guard `safeNext`); sign-up, sign-in, forgot and reset pages; `/auth/callback`; Google button; typed API client (token, one 401 refresh retry, error envelope, cold-start "waking up" banner). App shell: collapsible sidebar + mobile drawer, concept search, usage meter, user menu, theme sync to the profile, onboarding, dashboard, settings (JSON export, typed-confirmation delete), admin gate + `/admin/users`, placeholder pages for later phases (each names its phase). Public pages: landing (graph background, failure-case animation, pipeline, features, comparison), `/how-it-works` with the live graph, About, Privacy, Terms.
- Fixes during verification: reduced-motion users now see staged reveals at once (BUG-016); cold-start e2e waits and a `waitForResponse` race fixed (BUG-015, BUG-017); `/admin/users` split into a server page + client table so it can opt out of instant-navigation validation; marketing links to `/login` and `/signup` no longer prefetch the auth bundle (DEC-024).
**Files touched:** `supabase/` (config, .gitignore, migration 09), `apps/api/app/{auth,api,db,graph,core,main.py}`, `apps/api/tests/` (auth_helpers, test_auth_tokens, test_auth_api, test_graph_api, conftest, test_db_migrations), `apps/web/src/{proxy.ts,lib,components/{app,auth,marketing},app/{(auth),(marketing),app,admin,auth}}`, `apps/web/e2e/{auth.spec.ts,helpers.ts,design.spec.ts,screenshots.spec.ts}`, `docs/screenshots/phase4/`, `CLAUDE.md` (section 5: local auth stack commands), `progressfile.md`.
**Commands run & results:** ruff ✅ · ruff format ✅ (59 files) · mypy ✅ (43 files) · pytest ✅ 161 passed (live Neo4j + Postgres) · web lint ✅ · typecheck ✅ · prettier ✅ · vitest ✅ 103 · build ✅ (also with every `NEXT_PUBLIC_*` variable empty, as in CI) · Playwright ✅ 24/24 on two consecutive cold starts (`.next` deleted), plus 30/30 with `--repeat-each=3 --workers=4` for the auth spec · screenshots ✅ (12 in `docs/screenshots/phase4/`) · Lighthouse 12.6.1 on `next start`: desktop 100/100/100/100; mobile performance 74-80 with accessibility, best practices and SEO at 100.
**Manual verification:** API `/health` ok, `/graph` 200, `/me` without a token 401. The live e2e covers sign-up → confirmation mail in Mailpit → unconfirmed sign-in refused; sign-in → onboarding → dashboard (usage meter 0/40) → sign-out → `/app` redirects to login; a student gets the 403 page at `/admin/users` and 403/401 from the admin API; the theme chosen in settings follows the user to a fresh browser. Screenshots checked by eye in all three themes.
**Bugs found this session:** BUG-014, BUG-015, BUG-016, BUG-017
**Decisions:** DEC-023, DEC-024 (LIM-011 closed; LIM-015, LIM-016 added)
**Human action needed:** Autopilot State items 2 and 7-12.
**What we learned:**
- A `prefers-reduced-motion` rule that only shortens `animation-duration` is not enough: content revealed with `animation-delay` and fill-mode `both` stays invisible for the whole delay. Zero the delay too.
- A `waitForResponse` set up after the action that triggers the request is a race. Create the promise first, then act.
- On a dev server, e2e timings are dominated by first-request compilation; a test that passes warm can fail cold. Verify from a deleted `.next` before trusting a green run.
- Turbopack's dev cache can serve stale CSS after a file is restored with identical content. When the browser disagrees with the source, check what is actually served.
- Next.js `<Link>` prefetch adds the target route's JS to the current page's cost: public pages linking to the auth pages were loading supabase-js and zod until prefetch was turned off for those links.
**Next step:** Phase 5: LLM layer, quotas, cost, cache, guardrails.
---

## 7. Bug Log

### 7.1 Bug index

Severity: **S1** critical (data loss, security, app down) · **S2** major (feature broken) · **S3** minor (workaround exists) · **S4** cosmetic.

| ID | Date found | Phase | Severity | Area | Short symptom | Status | Fixed in commit | Regression test |
|---|---|---|---|---|---|---|---|---|
| BUG-001 | 2026-11-19 | 1 | S3 | db / dev env | `/health/deep` reported postgres `error` (password authentication failed) although the container was healthy | Fixed | Phase 1 build commit | `test_health_integration.py::test_postgres_reachable_and_pgvector_available` |
| BUG-002 | 2026-11-19 | 1 | S3 | backend | App import failed: SQLAlchemy asyncio requires greenlet | Fixed | Phase 1 api commit | every test in `tests/test_health.py` imports the app |
| BUG-003 | 2026-11-19 | 1 | S2 | frontend | shadcn init imported `cn` from an unvetted npm package; its `bg-muted` / `bg-accent` backgrounds clash with our muted (text) and accent (cyan) tokens | Fixed | Phase 1 web commit | `shared.test.tsx`, `contrast.test.ts`, visual check of `/design` |
| BUG-004 | 2026-11-19 | 1 | S3 | frontend | `link` variant of Button/Badge used `--primary` as text: 3.54:1 (Neon Noir) and 3.94:1 (Titanium Dark) on `--bg`, below AA | Fixed | `style(web): improve theme surface and accent contrast` | `src/test/contrast.test.ts` (accent text pairs); component uses accent |
| BUG-005 | 2026-11-19 | 1 | S2 | ci / frontend | GitHub Actions frontend job failed at `npm run typecheck`: `src/app/layout.tsx(17,50): error TS2304: Cannot find name 'LayoutProps'` | Fixed | `2fabc20` | The CI `typecheck` step itself (script now runs `next typegen` first); reproduced and verified from a fresh clone |
| BUG-006 | 2026-11-19 | 2 | S3 | backend | `scripts/seed_neo4j.py` run from the repo root reported NEO4J_* not set although `apps/api/.env` exists | Fixed | Phase 2 commit | `tests/test_graph_repository.py` (seeds via Settings from any cwd), manual run from repo root |
| BUG-007 | 2026-11-19 | 2 | S4 | backend | `ConceptId` required 2+ characters, rejecting valid one-letter ids used by fixtures and tests | Fixed | Phase 2 commit | `tests/test_graph_validation.py` |
| BUG-008 | 2026-11-19 | 3 | S3 | graph | `GraphRepository.delete_stale_chunks` ran a `DETACH DELETE` through the read-only helper: `Writing in read access mode not allowed` | Fixed | `efc832a` | `tests/test_graph_repository.py::test_seed_chunks_is_idempotent_and_removes_stale_chunks` |
| BUG-009 | 2026-11-19 | 3 | S4 | backend | `embed_pending` left an open read transaction, so callers could not `session.begin()` afterwards | Fixed | `efc832a` | `tests/test_content_db.py::test_only_changed_chunks_are_re_embedded` |
| BUG-010 | 2026-11-19 | 3 | S3 | tooling | Backslash sequences written through the shell tool were corrupted (`\\b` became a backspace control character in a regex; `\\n` became a real newline in a string), so the stray-text rule matched nothing and one helper had a syntax error | Fixed | `acd5c5f` | `tests/test_content_tooling.py::test_stray_self_correction_text_is_rejected`; repo scanned for control characters (none) |
| BUG-011 | 2026-11-19 | 3 | S3 | content | Authored `code_output` answers were wrong in 3 questions (amortized_analysis-q07, stack-q07, binary_search-q07) and a note contained a confused self-correction | Fixed | cluster commits | `tests/test_content_real.py::test_code_output_answers_match_real_program_output`; validator rejects stray self-correcting text |
| BUG-012 | 2026-11-19 | 3 | S4 | content | `dfs.md` Python snippet asserted interval nesting in one direction only, so the self-check would have failed for an ancestor/descendant pair taken in reverse order | Fixed before commit | `4d5d964` | snippet runner (`run_content_snippets.py`, `test_content_real.py`) |
| BUG-014 | 2026-11-19 | 4 | S3 | db / tooling | `scripts/migrate.py` run against the Supabase local database (already migrated by the Supabase CLI) failed half-way with `type "user_role" already exists` instead of refusing cleanly | Fixed | `feat(phase-04)` | `tests/test_db_migrations.py::test_supabase_cli_managed_database_is_refused` |
| BUG-013 | 2026-11-19 | 3 | S4 | content | `connectivity_scc-q04` option c had a 7-character `why_wrong` ("It can."), rejected by the question schema (minimum 10 characters) | Fixed before commit | `4d5d964` | `QuestionFile` schema in `validate_content.py` |
| BUG-015 | 2026-11-20 | 4 | S4 | e2e | Live auth e2e tests failed intermittently right after the dev server started: still on `/login` or `/app` when the 5 s URL assertion gave up | Fixed | `feat(phase-04)` | `e2e/auth.spec.ts` passes on two consecutive cold starts and 30/30 repeated runs |
| BUG-016 | 2026-11-20 | 4 | S3 | frontend / a11y | With reduced motion, the landing page's failure-case diagram hid its key node (Call Stack) for 2.8 s; the screenshot showed an arrow pointing at nothing | Fixed | `feat(phase-04)` | `e2e/design.spec.ts` "reduced motion shows the landing page's final state immediately" |
| BUG-017 | 2026-11-20 | 4 | S4 | e2e | Theme-sync e2e test could hang until timeout: `waitForResponse` for `PATCH /me` was registered after the click, so a fast response was missed | Fixed | `feat(phase-04)` | the test itself (promise created before the click) |

### 7.2 Bug details

> One block per bug. These are the most valuable study notes in the project, so be specific.

```
#### BUG-<nnn> — <short title>
- **Found:** <date>, Phase <x>, by <Claude Code | tester name | CI>
- **Severity / Area:** S<1-4> / <backend | frontend | graph | db | auth | llm | deploy | content>
- **Symptom:** what the user/test saw (error message, screenshot path)
- **Steps to reproduce:** 1… 2… 3…
- **Root cause:** the actual underlying reason (not the symptom)
- **Fix:** what changed and why that fixes the root cause
- **Files changed:**
- **Regression test:** test file::test name
- **Commit:**
- **Lesson / pattern to avoid:**
```

#### BUG-001 — Postgres health check fails against the healthy container
- **Found:** 2026-11-19, Phase 1, by Claude Code (manual run of `/health/deep`)
- **Severity / Area:** S3 / db (dev environment)
- **Symptom:** `{"postgres":{"status":"error","detail":"DBAPIError"}}`; underlying error `password authentication failed for user "cognexa"`, while `docker compose ps` showed postgres healthy and `psql` inside the container worked.
- **Steps to reproduce:** On a machine with a native Postgres on 5432: `docker compose up -d`, start the API with the example `.env`, `curl /health/deep`.
- **Root cause:** A native Windows Postgres listened on `0.0.0.0:5432` while Docker published on `[::]:5432`, so `localhost:5432` reached the wrong server. Not a code or credentials bug.
- **Fix:** Default host port for the container changed to 5433 (compose, root and API `.env.example`). The native server was left untouched.
- **Files changed:** `docker-compose.yml`, `.env.example`, `apps/api/.env.example`, README note.
- **Regression test:** `apps/api/tests/test_health_integration.py` (live; runs in CI and locally with env set)
- **Commit:** Phase 1 build commit (`build: docker compose for neo4j and pgvector`)
- **Lesson / pattern to avoid:** Port clashes masquerade as auth errors. Check the listener (`Get-NetTCPConnection -LocalPort`) before debugging credentials. Also: `/health/deep` returns only the exception class name by design, so reproduce with a script to see the real message.

#### BUG-002 — Missing greenlet for SQLAlchemy async
- **Found:** 2026-11-19, Phase 1, by Claude Code (first pytest run)
- **Severity / Area:** S3 / backend
- **Symptom:** `ImportError: The SQLAlchemy asyncio module requires that the Python 'greenlet' library is installed` at test collection.
- **Steps to reproduce:** `uv add sqlalchemy` (without the extra), import `sqlalchemy.ext.asyncio`.
- **Root cause:** I added `sqlalchemy` without its `asyncio` extra; greenlet is not pulled in automatically.
- **Fix:** `uv add "sqlalchemy[asyncio]"` (adds greenlet 3.5.6).
- **Files changed:** `apps/api/pyproject.toml`, `apps/api/uv.lock`
- **Regression test:** all API tests import `app.main`, which imports the async engine.
- **Commit:** Phase 1 api commit (`feat(api): fastapi app factory, config, health endpoints`)
- **Lesson / pattern to avoid:** Install SQLAlchemy async as `sqlalchemy[asyncio]`.

#### BUG-003 — shadcn init output unsafe / incompatible with our tokens
- **Found:** 2026-11-19, Phase 1, by Claude Code (reading generated files)
- **Severity / Area:** S2 / frontend
- **Symptom:** `components/ui/*` imported `{ cn } from "cn"`, a package named `cn` added to dependencies (not clsx + tailwind-merge). Separately, shadcn used `bg-muted` / `bg-accent` as backgrounds, but in our design `muted` is a text colour and `accent` is cyan, which would have produced grey/cyan hover backgrounds.
- **Root cause:** Generator defaults; our spec (CLAUDE.md §6) reuses the names `muted` and `accent` with different meanings.
- **Fix:** Standard `clsx` + `tailwind-merge` `cn` in `src/lib/utils.ts`, removed the `cn` package, rewrote ui imports to `@/lib/utils`, mapped shadcn background uses to `bg-surface-2` / `text-text`.
- **Files changed:** `src/lib/utils.ts`, `src/components/ui/*.tsx`, `src/app/globals.css`
- **Regression test:** `src/test/contrast.test.ts`, component tests, visual review of `/design` (no dedicated test guards against the generator reintroducing it; see LIM-006).
- **Commit:** Phase 1 web commit (`feat(web): next.js app with tailwind and shadcn/ui`)
- **Lesson / pattern to avoid:** After `npx shadcn add`, re-check for `bg-muted` / `bg-accent` / `text-accent-foreground` and the `cn` import in new files.

#### BUG-004 — Link variant uses primary colour as text (fails AA on dark themes)
- **Found:** 2026-11-19, Phase 1 follow-up, by Claude Code (visual review of the Titanium Dark screenshot, then measured)
- **Severity / Area:** S3 / frontend
- **Symptom:** The `Link` button in `/design` is red (Titanium Dark) or purple (Neon Noir) text on near-black: 3.94:1 and 3.54:1, below the 4.5:1 AA requirement. CLAUDE.md section 6 also says purple is not for body text on black.
- **Steps to reproduce:** Open `/design` in Neon Noir or Titanium Dark and look at the `Link` button.
- **Root cause:** shadcn's `link` variant is `text-primary`; our primary colours are fill colours chosen for white-on-primary contrast, not for use as text on `--bg`. The contrast test only checked a fixed list of token pairs, none of which was primary-as-text.
- **Fix:** `link` variant in `button.tsx` and `badge.tsx` now uses `text-accent` (>= 4.5:1 on bg/surface/surface-2 in all three themes after the accent fix).
- **Files changed:** `apps/web/src/components/ui/button.tsx`, `apps/web/src/components/ui/badge.tsx`
- **Regression test:** `src/test/contrast.test.ts` accent-as-text pairs (guards the colour the variant now uses); nothing yet prevents `text-primary` from being reintroduced (see LIM-006).
- **Commit:** `style(web): improve theme surface and accent contrast`
- **Lesson / pattern to avoid:** Primary is a fill colour. Use accent (or text/muted) for text and link-like elements.

#### BUG-005 — CI typecheck fails: Cannot find name 'LayoutProps'
- **Found:** 2026-11-19, Phase 1 (after merge), by CI (GitHub Actions frontend job)
- **Severity / Area:** S2 / ci, frontend
- **Symptom:** `npm run typecheck` fails with `src/app/layout.tsx(17,50): error TS2304: Cannot find name 'LayoutProps'.`; passes locally.
- **Steps to reproduce:** Fresh checkout (or `rm -rf apps/web/.next apps/web/next-env.d.ts`), `npm ci`, `npm run typecheck`. Reproduced locally with `.next` deleted: same error.
- **Root cause:** Next.js 16 generates the global route helper types (`LayoutProps`, `PageProps`) into `.next/types` (plus `next-env.d.ts`). Both are gitignored and only exist after `next dev` or `next build`. Locally they were always present; in CI `typecheck` runs before `build`, so `tsc` ran without them.
- **Fix:** `"typecheck": "next typegen && tsc --noEmit"`. `next typegen` exists in the installed Next.js 16.4.6 (`next typegen --help`) and generates the types without a full build; it also writes `next-env.d.ts`.
- **Files changed:** `apps/web/package.json`
- **Regression test:** the CI `typecheck` step itself. Verified by deleting `.next` and `next-env.d.ts` and running `npm ci && lint && typecheck && test && build` (all pass), then again in a fresh `git clone` of the repo (backend and frontend jobs, no `.env`, no `.venv`, no `node_modules`).
- **Commit:** `2fabc20 fix(ci): generate next.js route types before typecheck (BUG-005)`
- **Lesson / pattern to avoid:** "Works locally" is not "works in CI" when gitignored generated files are involved. Prove CI steps in a fresh clone, not in the dev working tree. This is LIM-005 materialising.

#### BUG-006 — Settings read `.env` relative to the working directory
- **Found:** 2026-11-19, Phase 2, by Claude Code (first run of `scripts/seed_neo4j.py` from the repo root)
- **Severity / Area:** S3 / backend
- **Symptom:** `ERROR: NEO4J_URI / NEO4J_USER / NEO4J_PASSWORD are not set` even though `apps/api/.env` has them.
- **Steps to reproduce:** from the repository root run `uv run --project apps/api python scripts/seed_neo4j.py`.
- **Root cause:** `SettingsConfigDict(env_file=".env")` is resolved against the current directory, so only commands run from `apps/api` found the file. Phase 1 never ran a script from another directory.
- **Fix:** `ENV_FILE = Path(__file__).resolve().parents[2] / ".env"` in `app/core/config.py` (absolute, independent of cwd).
- **Files changed:** `apps/api/app/core/config.py`
- **Regression test:** all live-DB tests build `Settings()` and run from `apps/api`; the scripts run from the repo root in CI (`../../scripts/...`) and locally.
- **Commit:** Phase 2 commit
- **Lesson / pattern to avoid:** Never rely on the working directory for config paths.

#### BUG-007 — Concept id minimum length too strict
- **Found:** 2026-11-19, Phase 2, by Claude Code (15 validator tests failed)
- **Severity / Area:** S4 / backend
- **Symptom:** pydantic `ValidationError` on ids such as `a`, `b`.
- **Root cause:** I declared `ConceptId` with `min_length=2` although the real rule is the snake_case pattern.
- **Fix:** `min_length=1`; the `^[a-z][a-z0-9_]*$` pattern remains the real constraint.
- **Files changed:** `apps/api/app/graph/models.py`
- **Regression test:** `tests/test_graph_validation.py` (single-letter ids; cyclic fixture)
- **Commit:** Phase 2 commit
- **Lesson / pattern to avoid:** Keep one source of truth for a constraint.

#### BUG-008 — Neo4j write executed through the read-only transaction helper
- **Found:** 2026-11-19, Phase 3, by Claude Code (new integration test)
- **Severity / Area:** S3 / graph
- **Symptom:** `Neo.ClientError.Statement.AccessMode: Writing in read access mode not allowed` when removing stale chunks.
- **Root cause:** `delete_stale_chunks` reused `_read` (an `execute_read` transaction) for a `DETACH DELETE`.
- **Fix:** added a `_write` helper (`execute_write`) and used it.
- **Files changed:** `apps/api/app/graph/repository.py`
- **Regression test:** `test_seed_chunks_is_idempotent_and_removes_stale_chunks`
- **Commit:** `efc832a`
- **Lesson / pattern to avoid:** Keep read and write helpers separate and name them clearly; the driver enforces access mode per transaction.

#### BUG-009 — Embedding helper left a read transaction open
- **Found:** 2026-11-19, Phase 3, by Claude Code (test failed with "A transaction is already begun on this Session")
- **Severity / Area:** S4 / backend
- **Root cause:** after the final empty batch query the session had autobegun a transaction that was never ended.
- **Fix:** `await session.commit()` before returning from `embed_pending`.
- **Files changed:** `apps/api/app/content/vectors.py`
- **Regression test:** `test_only_changed_chunks_are_re_embedded`
- **Commit:** `efc832a`
- **Lesson / pattern to avoid:** Helpers that take a session should leave it in a clean state.

#### BUG-012 — One-sided interval-nesting assertion in the DFS note
- **Found:** 2026-11-19, Phase 3, by Claude Code (reviewing the snippet before running it)
- **Severity / Area:** S4 / content
- **Symptom:** the check `disc[u] < disc[v] < fin[v] < fin[u] or disjoint` is false when v is an ancestor of u, so the snippet's own self-check would fail for the pair (u, v) = (3, 0).
- **Root cause:** the parenthesis theorem is symmetric (either interval may contain the other); the assertion only covered u containing v.
- **Fix:** loop over pairs and accept "u contains v", "v contains u" or disjoint.
- **Files changed:** `data/subjects/dsa/content/dfs.md`
- **Regression test:** the snippet itself is executed by `run_content_snippets.py` / `test_content_real.py`.
- **Commit:** `4d5d964`
- **Lesson / pattern to avoid:** when a property is symmetric, assert both orientations or iterate over unordered pairs.

#### BUG-013 — `why_wrong` too short to pass the schema
- **Found:** 2026-11-19, Phase 3, by `validate_content.py`
- **Severity / Area:** S4 / content
- **Symptom:** `connectivity_scc: questions file invalid ... incorrect option 'c' needs a why_wrong explanation`.
- **Root cause:** the explanation "It can." is shorter than the 10-character minimum, which exists so every distractor gets a real explanation.
- **Fix:** replaced it with a full sentence.
- **Files changed:** `data/subjects/dsa/questions/connectivity_scc.yaml`
- **Regression test:** `QuestionFile` validation (runs in CI via `validate_content.py --strict`).
- **Commit:** `4d5d964`
- **Lesson / pattern to avoid:** treat schema minimums as a writing standard, not an obstacle.

#### BUG-010 — Backslashes corrupted by the shell tool layer
- **Found:** 2026-11-19, Phase 3, by Claude Code (a validator test that should fail passed; a script had a syntax error)
- **Severity / Area:** S3 / tooling
- **Symptom:** The stray-text regex `\b(...)` silently matched nothing; `"\n".join(...)` became a string containing a real newline.
- **Root cause:** escape sequences inside heredocs passed through the shell tool were interpreted before reaching the file (`\b` became 0x08).
- **Fix:** rewrote the regex without backslashes (lookarounds built from plain strings), replaced the newline join with `chr(10)`, and scanned all repository files for control characters (none left). Code containing backslashes is now written with the file-writing tool.
- **Files changed:** `apps/api/app/content/validation.py`, `apps/api/app/content/snippets.py`
- **Regression test:** `test_stray_self_correction_text_is_rejected`
- **Commit:** `acd5c5f`
- **Lesson / pattern to avoid:** When a test that should fail passes, suspect the test input pipeline, not only the code.

#### BUG-011 — Wrong authored answer keys and a stray self-correction in content
- **Found:** 2026-11-19, Phase 3, by the code-output verifier and by review
- **Severity / Area:** S3 / content
- **Symptom:** `expected '10 8' but program printed '12 8'` (amortized_analysis-q07); `expected 'abcd 4' but ... 'ab(d 4'` (stack-q07); `expected '5 3' ... '5 2'` (binary_search-q07); and a note contained "wait, that window is [1, 3, 2]...".
- **Root cause:** answers were written from mental tracing instead of being run; one explanation was left half-corrected.
- **Fix:** corrected the keys and explanations; replaced stack-q07; added the machine verification as a permanent test and a validator rule for unfinished text.
- **Files changed:** the three question files, `sliding_window.md`, validator.
- **Regression test:** `test_code_output_answers_match_real_program_output`, `test_stray_self_correction_text_is_rejected`
- **Commit:** cluster commits (complexity, linear, searching_hashing)
- **Lesson / pattern to avoid:** Never trust a hand-traced expected output; run it.

#### BUG-014 — `migrate.py` half-applied on a Supabase-CLI-managed database
- **Found:** 2026-11-19, Phase 4, while pointing local tooling at the Supabase local stack
- **Severity / Area:** S3 / db tooling
- **Symptom:** `type "user_role" already exists`; a stray `public.schema_migrations` table was left behind.
- **Root cause:** the Supabase CLI had already applied the migrations (tracked in `supabase_migrations.schema_migrations`); `migrate.py` keeps its own ledger and started from zero.
- **Fix:** `migrate.py` raises `MigrationError` ("managed by the Supabase CLI") when the `supabase_migrations` schema exists; the stray table was dropped.
- **Files changed:** `apps/api/app/db/migrate.py`
- **Regression test:** `test_supabase_cli_managed_database_is_refused`
- **Commit:** `feat(phase-04)`
- **Lesson / pattern to avoid:** Two migration runners must never share a database; make the wrong one refuse loudly.

#### BUG-015 — Cold-start flakiness in live auth e2e tests
- **Found:** 2026-11-20, Phase 4 verification
- **Severity / Area:** S4 / e2e
- **Symptom:** `expect(page).toHaveURL(/app/onboarding/)` timed out (received `/login` or `/app`) on the first run after the dev server started; later runs passed.
- **Root cause:** the dev server compiles `/app` and `/app/onboarding` on first request, which took longer than the default 5 s expect timeout; one test (two sign-ins + onboarding) could also exceed the 30 s test timeout.
- **Fix:** a named `NAV_TIMEOUT` (30 s) only on the navigation waits after sign-in, and `test.slow()` for the live block. The assertions are unchanged.
- **Files changed:** `apps/web/e2e/auth.spec.ts`
- **Regression test:** two consecutive cold-start runs (`.next` deleted), 24/24
- **Commit:** `feat(phase-04)`
- **Lesson / pattern to avoid:** Verify e2e from a cold server; warm runs hide compile time.

#### BUG-016 — Reduced motion delayed content instead of removing motion
- **Found:** 2026-11-20, Phase 4, by looking at the generated screenshots
- **Severity / Area:** S3 / frontend, accessibility
- **Symptom:** the failure-case diagram showed "needs →" pointing at empty space; the Call Stack node (the point of the diagram) appeared only after 2.8 s for reduced-motion users.
- **Root cause:** the global `prefers-reduced-motion` rule shortened `animation-duration` but not `animation-delay`; staged reveals use delays with fill-mode `both`, so elements stayed at opacity 0 for the whole delay.
- **Fix:** `animation-delay: 0s !important` in the reduced-motion rule (fixes every staged animation).
- **Files changed:** `apps/web/src/app/globals.css`
- **Regression test:** `e2e/design.spec.ts` "reduced motion shows the landing page's final state immediately" (fails with opacity 0 without the rule)
- **Commit:** `feat(phase-04)`
- **Lesson / pattern to avoid:** Look at the screenshots, not only at green tests.

#### BUG-017 — `waitForResponse` registered after the triggering click
- **Found:** 2026-11-20, Phase 4 verification
- **Severity / Area:** S4 / e2e
- **Symptom:** "theme choice ... follows the user to a new browser" sometimes hit the test timeout.
- **Root cause:** the `PATCH /me` could complete before `page.waitForResponse` was called, so the wait never resolved.
- **Fix:** create the response promise before clicking, then await it and assert `ok()`.
- **Files changed:** `apps/web/e2e/auth.spec.ts`
- **Regression test:** the test itself, 30/30 repeated runs
- **Commit:** `feat(phase-04)`
- **Lesson / pattern to avoid:** Listen first, act second.

---

## 8. Decisions Log (lightweight ADRs)

| ID | Date | Decision | Alternatives considered | Reason | Consequences |
|---|---|---|---|---|---|
| DEC-001 | 2026-11-19 | Single subject first (DSA), subject-agnostic schema | Multi-subject from day one; "any PDF" | Graph quality must be verifiable; evaluation needs gold answers; avoids competing head-on with NotebookLM | Other subjects become content packs later |
| DEC-002 | 2026-11-19 | Separate FastAPI backend (Render) + Next.js (Vercel) | All-in-Next.js on Vercel | Python AI/eval ecosystem, team skills, clear 3-component architecture for the report | Render free cold start → warm-up banner + keep-alive |
| DEC-003 | 2026-11-19 | Rule-based recommender (not ML) | Deep Knowledge Tracing, BKT | Matches report scope; explainable; no training data needed | ML mastery predictor listed as future work |
| DEC-004 | 2026-11-19 | Bounded agentic controller (max 2 steps) instead of multi-agent | GraphMASAL-style multi-agent [19] | Justifies "Agentic" in the title while staying debuggable | Feature-flagged (AGENTIC_MODE) |
| DEC-005 | 2026-11-19 | Plain RAG baseline uses the same chunks as GraphRAG | Separate corpus | Fair comparison: only the retrieval method differs | — |
| DEC-006 | 2026-11-19 | Groq primary LLM, Gemini fallback + embeddings; model IDs via env | Single provider | Free tiers are rate-limited and change often | Provider layer must stay abstract |
| DEC-007 | 2026-11-19 | Keep create-next-app defaults for Next.js 16 (`cacheComponents`, `partialPrefetching`) | Disable them | They are the current stable defaults; docs say both become standard in the next major | Dynamic data access in server components must sit under Suspense; revisit in Phase 4 when auth lands |
| DEC-008 | 2026-11-19 | Tailwind `muted` / `accent` follow CLAUDE.md §6 (text / cyan); shadcn background uses remapped to `surface-2` | Keep shadcn semantics and expose project tokens under other names | The spec names the tokens muted and accent | Newly added shadcn components need the same fix (LIM-006) |
| DEC-009 | 2026-11-19 | Local Postgres published on host port 5433 | Stop the native Postgres; keep 5432 | Do not touch the user's installed database | Local `DATABASE_URL` uses 5433; the CI service container still uses 5432 |
| DEC-010 | 2026-11-19 | Own ThemeProvider (`useSyncExternalStore` over `data-theme`) + inline no-flash script instead of next-themes | next-themes | Three named themes, no system/class modes needed, fewer deps; next-themes removed | Profile sync in Phase 4 hooks into `setTheme` |
| DEC-011 | 2026-11-19 | Vitest without `@vitejs/plugin-react`; `@types/node` bumped to 22 | Install the plugin with `--legacy-peer-deps` | The plugin caused a Babel peer-dependency conflict with shadcn's deps and is not needed for these tests; Vitest 5 requires `@types/node` 22+ | Avoid `--legacy-peer-deps` so the lockfile stays honest |
| DEC-012 | 2026-11-19 | **SUPERSEDED by DEC-013.** Team commits directly on `main`: no feature branches, no PRs. Before every commit run full verification for the touched app; `git pull --rebase` before a session and before pushing; push at the end of each phase (or sooner) and watch CI; a red CI is fixed before any new work; tag each finished phase (v0.N) on `main`; Claude Code does not push or tag unless asked. (Requested as DEC-008, but that ID was already taken by the Tailwind muted/accent mapping, so it is recorded as DEC-012.) | Phase branches + PRs with review (previous Appendix D workflow, used once for Phase 1 via PR #1) | Small team, simpler flow, CI watched after each push | No review record per phase; a broken push blocks everyone. `docs/PHASE0_SETUP.md` step 5 changed: do not require PRs or status checks on `main` (they would reject direct pushes). **Check the GitHub ruleset if one was already created from the old instructions.** |
| DEC-013 | 2026-11-19 | Single developer, single branch: the human works alone on `main`. Never create branches, PRs or worktrees. Before each commit run the full verification for the touched app; small Conventional Commits as listed per phase in Appendix D. At the end of each phase the human pushes, watches CI and tags `v0.N` once green; red CI is fixed before new work. Claude Code never pushes or tags and gives the commands. Team-workflow wording (reviews/approvals, spreading commits across teammates, `git pull --rebase` routine) removed; one-line note kept: run `git pull` first only when committing from another machine or the GitHub web UI. Content review checklist: the reviewer is the human developer. GitHub ruleset optional (block force pushes only). | DEC-012 (team commits on `main` with a rebase routine); phase branches + PRs | The project is now developed by one person; the extra process added no value | No second reviewer: correctness relies on tests, CI and the human's own review. PHASE0_SETUP changed: Supabase built-in email only reaches organisation members (now: the developer's own addresses), so sign-up tests use own addresses until custom SMTP. Other team-oriented Phase 0 steps (shared team Google account, GitHub org with four owners, four test users) were not changed. |
| DEC-014 | 2026-11-19 | `content_chunks.embedding` is `vector(768)` fixed in SQL; EMBEDDING_DIM must match; changing it needs a new migration + re-embedding (documented in the migration and `.env.example`) | Template the dimension into SQL at apply time | The Supabase CLI applies raw SQL, so templating would fork the migration path | `seed_vectors.py` (Phase 3) must refuse to run on a mismatch |
| DEC-015 | 2026-11-19 | Migrations are plain SQL in `supabase/migrations`; `scripts/migrate.py` (checksummed, advisory-locked) applies them to local/CI Postgres, with `supabase/shim/auth_shim.sql` imitating `auth.users`/`auth.uid()`/roles; Supabase itself uses `supabase db push` | Alembic; separate CI-only schema | One set of SQL for both targets, as CLAUDE.md requires | The shim is test-only and must never be applied to Supabase |
| DEC-016 | 2026-11-19 | SQLAlchemy Core table definitions (not ORM), drift-tested against the real schema | ORM models | Repositories use explicit statements; Core keeps SQL close; the drift test keeps SQL as the source of truth | Every new table needs a Core definition (test fails otherwise) |
| DEC-017 | 2026-11-19 | RELATED_TO stored once (smaller id to larger id) and queried undirected; PREREQUISITE_OF edges are cycle-checked inside the write transaction; cycle checks count proposed edges too | Store both directions; check cycles in callers | No duplicates; the DAG rule cannot be bypassed; approving a proposal can never create a cycle | A concurrent pair of writes could still race (single admin editor, acceptable; LIM-012) |
| DEC-018 | 2026-11-19 | Seeds are additive by default; `--prune` removes only human-sourced edges missing from the file; seed/migrate scripts refuse non-local databases without `--allow-remote`; `--wipe` requires typing WIPE | Always prune; no guards | Protects LLM-proposed edges, admin edits and production data | Autopilot never uses `--allow-remote` |
| DEC-019 | 2026-11-19 | Autopilot mode: one commit per phase and `git push origin main` are authorised by the human's AUTOPILOT prompt; tags are never created. CLAUDE.md section 9 records this exception | Per-step commits and manual pushes (DEC-013) | Explicit user instruction for autonomous operation | Per-phase commits are large; DEC-013's small-commit rule applies again outside autopilot |
| DEC-020 | 2026-11-19 | Phase 3 is committed per content cluster (`content(<cluster>): ...`), each followed by a push, instead of one commit per phase | One huge phase commit | Appendix D lists per-cluster commits; the phase is far too large for a single commit and clusters are natural, verifiable checkpoints | The phase still ends with a `feat(phase-03)`-style wrap-up commit for tooling/seeds/eval set |
| DEC-021 | 2026-11-19 | Question conventions: q01 and q02 are parallel difficulty-1 MCQs; q03 and q04 are parallel difficulty-2 MCQs; q05 multi_select, q06 true_false, q07 code_output, q08 short_answer. Parallel pairs feed the pre/post study sets and quiz variety. `code_output` answers are machine-verified by running the program; incorrect MCQ options must carry `why_wrong` | Free-form question sets | Makes matched study forms possible and keeps answer keys honest | Authoring cost is higher; schema enforces the rules |
| DEC-023 | 2026-11-19 | Auth: Supabase access tokens are verified in FastAPI against the project JWKS (asymmetric keys), with HS256 only if a legacy secret is configured; roles are read from `public.profiles` (cached 30 s), never from token claims; account deletion goes through the Auth admin API with the service-role key | Trust a role claim in the JWT; verify with the shared secret only | Supabase now issues asymmetric signing keys; an admin must be able to change roles without re-issuing tokens | A role change takes up to 30 s to apply (LIM-016); the service-role key stays backend-only |
| DEC-024 | 2026-11-20 | Keep `cacheComponents` + `partialPrefetching` on with Supabase SSR (closes LIM-011): session refresh lives in `src/proxy.ts`, app pages read the user client-side through TanStack Query, so prerendered shells stay static. Marketing links to `/login` and `/signup` use `prefetch={false}`; `/admin/users` exports `instant = false` (client page behind a gate) | Turn both flags off; prefetch everything | Every route except `/auth/callback` still prerenders; prefetching the auth pages loaded supabase-js + zod on every public page view | Signed-in pages show skeletons until `/me` resolves; the auth pages' JS is fetched on click |
| DEC-022 | 2026-11-19 | Content code samples are C++14 (not 17) and Python 3.12; every snippet is a complete program that asserts its own claims and is compiled/run by the test suite | C++17 | The only local compiler is MinGW GCC 6.3 (no `-std=c++17`); C++14 also works on every CI compiler | Notes avoid C++17 features (structured bindings, `std::optional`) |

---

## 9. Known Limitations & Tech Debt

| ID | Description | Impact | Plan |
|---|---|---|---|
| LIM-001 | Free-tier cold starts (Render ~1 min) | First request slow | Warm-up on page load; keep-alive; paid instance if ever needed |
| LIM-002 | No managed backups on free tiers | Data-loss risk | Manual backup script (Phase 13); Neo4j re-seedable from YAML |
| LIM-003 | Per-minute rate limiter is in-memory | Only correct with one backend instance | Fine on Render free (1 instance); move to Redis if scaled |
| LIM-004 | LLM free-tier quotas | Global daily cap may be hit during heavy use | Quotas, caching, AI-free Review mode still works |
| LIM-005 | CI workflow was first run on GitHub after the Phase 1 merge and failed (BUG-005). The fix is verified only by reproducing CI steps in a fresh local clone, not yet by a green GitHub run | A remaining Linux/Windows or network difference could still fail | Push, watch the run, record the result in Session 4 / next phase |
| LIM-006 | shadcn token remap (DEC-008) is applied by hand to generated files | New `npx shadcn add` components reintroduce `bg-muted` / `bg-accent` / the wrong `cn` import | After each add: grep and fix; consider a lint rule later |
| LIM-007 | ~~Titanium Light `--accent` (#8A9099) about 3.2:1 on white; Neon Noir `--surface` vs `--bg` subtle~~ **CLOSED 2026-11-19** (Session 2): accent now #5F6670 (5.80:1 on white); Neon Noir surface #17142A / surface-2 #231E38 / border #332C4D (surface 1.13:1, surface-2 1.26:1, border 1.55:1 vs bg) | Was: accent unusable as small text in Titanium Light; panels relied on thin borders | Contrast tests now also cover accent text and panel distinctness for all three themes |
| LIM-008 | `/design` is gated by NODE_ENV only | Any non-production deployment exposes it | Acceptable: it holds no data |
| LIM-009 | `/health/deep` is unauthenticated and reveals dependency status | Minor information disclosure | Reduce detail or protect in Phase 13 |
| LIM-010 | `statement_cache_size=0` / `prepared_statement_cache_size=0` set only on the health-check engine | The shared engine in Phase 2 must apply the same settings (CLAUDE.md rule 6) | Put them in one engine factory in Phase 2 |
| LIM-011 | ~~**Phase 4:** Phase 4 must verify Supabase SSR auth works with Next.js cacheComponents/partialPrefetching (DEC-007); if it causes problems, disable them and record a new decision. | Auth cookies / session reads are dynamic data and may conflict with the prerendered shell | Verify in Phase 4 before building the app shell; if problematic set both flags off in `next.config.ts` and log a DEC~~ **CLOSED 2026-11-20** (DEC-024: works with both flags on) |
| LIM-012 | Concurrent `upsert_edge` calls could both pass the cycle check and create a cycle together | DAG rule violation under a race | Single admin editor; `validate_graph.py` and CI catch it; add a Neo4j-side lock if multi-admin editing is ever needed |
| LIM-013 | Migrations were tested on plain Postgres 16 + shim, not on a real Supabase project or the Supabase CLI. **Update 2026-11-19:** all 9 apply cleanly on the Supabase CLI local stack (Postgres 17); a cloud project is still untested | Supabase-specific differences (extension schema, default grants, managed roles) could surface at deploy | Phase 4 tries the Supabase local stack; Phase 15 runbook includes `supabase db push` on dev first |
| LIM-014 | `/health/deep` and tests share one local Neo4j/Postgres that also holds dev data | A test bug could touch dev data | Tests use unique ids/subjects and throwaway databases; never `wipe()` in tests |
| LIM-015 | Lighthouse mobile performance on the landing page is 74-80 locally (desktop 100; accessibility, best practices and SEO 100). The cost is React hydration (~770 ms under 4× CPU throttling) and layout, measured on a busy dev laptop | Below the 90 target in lab conditions | Re-measure on Vercel (Human Action 11); if still low, Phase 13 options: keep TanStack/Toaster providers out of marketing routes (separate root layouts), lighter hero |
| LIM-016 | Role changes take up to 30 s to apply (profile cache, DEC-023) | A demoted admin keeps access for up to 30 s | Acceptable for this app; revisit if roles ever guard sensitive data |

---

## 10. Free-Tier Watch

| Service | Limit | Our mitigation | Current usage (update monthly) |
|---|---|---|---|
| Neo4j Aura Free | Pause after 72 h idle; node/relationship caps | Daily keep-alive; re-seed script | ~69 concepts + ~700 chunks |
| Supabase Free | 500 MB DB; pause ~7 days idle; 2 projects; default email sender = team only, ~2/hour | Keep-alive; prune old cache rows; custom SMTP | |
| Render Free | 15 min sleep; 750 h/month; 512 MB RAM | 1 worker; warm-up | |
| Vercel Hobby | Non-commercial; function limits | Static where possible | |
| Groq Free | RPM/RPD/TPM per model | Quotas + fallback + cache | |
| Gemini Free | Low RPD; data may be used for product improvement | Embeddings cached; no PII in prompts | |
| GitHub Actions | Scheduled jobs pause after 60 days of inactivity | Keep committing / re-enable | |

---

## 11. Environment Variables Reference (names only, never values)

| Variable | Where | Purpose |
|---|---|---|
| `DEFAULT_SUBJECT_ID` | api | Subject loaded by seed scripts (default `dsa`) |
| `SUPABASE_JWT_SECRET` | api | Legacy HS256 JWT secret (phase 4, optional) |
| `NEXT_PUBLIC_SENTRY_DSN` (optional) | web | Browser error tracking |
| `APP_ENV`, `LOG_LEVEL`, `HEALTH_CHECK_TIMEOUT_S` | api | Runtime label, log level, per-dependency probe timeout for /health/deep |
| `ALLOWED_ORIGINS` | api | CORS origins |
| `NEO4J_HTTP_PORT`, `NEO4J_BOLT_PORT`, `POSTGRES_PORT`, `POSTGRES_USER`, `POSTGRES_PASSWORD`, `POSTGRES_DB` | root .env (docker compose) | Local container ports and credentials (Postgres host port defaults to 5433) |
| `DATABASE_URL` | api | Supabase Postgres (pooler) |
| `SUPABASE_URL`, `SUPABASE_SERVICE_ROLE_KEY`, `SUPABASE_JWKS_URL` | api | Admin ops + JWT verification |
| `NEO4J_URI`, `NEO4J_USER`, `NEO4J_PASSWORD` | api | Graph DB |
| `LLM_PRIMARY_PROVIDER`, `LLM_PRIMARY_MODEL` | api | Main model |
| `LLM_FALLBACK_PROVIDER`, `LLM_FALLBACK_MODEL` | api | Fallback model |
| `LLM_JUDGE_PROVIDER`, `LLM_JUDGE_MODEL` | api, eval | Short-answer grading + RAGAs judge |
| `EMBEDDING_PROVIDER`, `EMBEDDING_MODEL`, `EMBEDDING_DIM` | api | Embeddings |
| `GROQ_API_KEY`, `GEMINI_API_KEY` | api | Provider keys |
| `AGENTIC_MODE`, `STUDY_MODE` | api | Feature flags (defaults; admin can override) |
| `NEXT_PUBLIC_SUPABASE_URL`, `NEXT_PUBLIC_SUPABASE_ANON_KEY` | web | Supabase client (public) |
| `NEXT_PUBLIC_API_URL` | web | Backend base URL |
| `SENTRY_DSN` (optional) | api, web | Error tracking |

_(Claude Code: keep this in sync with both .env.example files.)_

---

## 12. Content Review Checklist

> The reviewer is me (the sole developer). I tick a concept only after checking its notes, code and questions, and then set `reviewed: true` in the note's frontmatter.
> `Written` is generated from the files by `scripts/update_review_checklist.py`; the other columns are mine and are preserved when the table is regenerated.

| Cluster | Concept | Written | Notes reviewed | Questions reviewed | Reviewer (me) | Date |
|---|---|---|---|---|---|---|
| foundations | discrete_math_basics | notes + questions | ☐ | ☐ |  |  |
| foundations | variables_memory | notes + questions | ☐ | ☐ |  |  |
| foundations | control_flow | notes + questions | ☐ | ☐ |  |  |
| foundations | functions | notes + questions | ☐ | ☐ |  |  |
| foundations | arrays | notes + questions | ☐ | ☐ |  |  |
| foundations | strings | notes + questions | ☐ | ☐ |  |  |
| foundations | pointers_references | notes + questions | ☐ | ☐ |  |  |
| foundations | stack_heap_memory | notes + questions | ☐ | ☐ |  |  |
| foundations | call_stack | notes + questions | ☐ | ☐ |  |  |
| foundations | bit_manipulation | notes + questions | ☐ | ☐ |  |  |
| foundations | recursion | notes + questions | ☐ | ☐ |  |  |
| complexity | time_complexity | notes + questions | ☐ | ☐ |  |  |
| complexity | asymptotic_notation | notes + questions | ☐ | ☐ |  |  |
| complexity | space_complexity | notes + questions | ☐ | ☐ |  |  |
| complexity | recurrence_relations | notes + questions | ☐ | ☐ |  |  |
| linear | dynamic_arrays | notes + questions | ☐ | ☐ |  |  |
| complexity | amortized_analysis | notes + questions | ☐ | ☐ |  |  |
| linear | singly_linked_list | notes + questions | ☐ | ☐ |  |  |
| linear | doubly_circular_linked_list | notes + questions | ☐ | ☐ |  |  |
| linear | stack | notes + questions | ☐ | ☐ |  |  |
| linear | queue | notes + questions | ☐ | ☐ |  |  |
| linear | deque_circular_queue | notes + questions | ☐ | ☐ |  |  |
| linear | priority_queue_adt | notes + questions | ☐ | ☐ |  |  |
| linear | expression_evaluation | notes + questions | ☐ | ☐ |  |  |
| linear | monotonic_stack | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | linear_search | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | binary_search | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | two_pointers | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | sliding_window | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | prefix_sums | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | hash_functions | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | hash_tables | notes + questions | ☐ | ☐ |  |  |
| searching_hashing | hash_sets_maps | notes + questions | ☐ | ☐ |  |  |
| sorting | elementary_sorts | notes + questions | ☐ | ☐ |  |  |
| sorting | divide_and_conquer | notes + questions | ☐ | ☐ |  |  |
| sorting | merge_sort | notes + questions | ☐ | ☐ |  |  |
| sorting | quick_sort | notes + questions | ☐ | ☐ |  |  |
| sorting | non_comparison_sorts | notes + questions | ☐ | ☐ |  |  |
| trees | tree_basics | notes + questions | ☐ | ☐ |  |  |
| sorting | sorting_lower_bound | notes + questions | ☐ | ☐ |  |  |
| trees | binary_tree | notes + questions | ☐ | ☐ |  |  |
| trees | dfs_tree_traversals | notes + questions | ☐ | ☐ |  |  |
| trees | level_order_traversal | notes + questions | ☐ | ☐ |  |  |
| trees | bst | notes + questions | ☐ | ☐ |  |  |
| trees | binary_heap | notes + questions | ☐ | ☐ |  |  |
| sorting | heap_sort | notes + questions | ☐ | ☐ |  |  |
| trees | avl_tree | notes + questions | ☐ | ☐ |  |  |
| trees | red_black_tree | notes + questions | ☐ | ☐ |  |  |
| trees | b_tree | notes + questions | ☐ | ☐ |  |  |
| trees | trie | notes + questions | ☐ | ☐ |  |  |
| trees | segment_tree | notes + questions | ☐ | ☐ |  |  |
| trees | fenwick_tree | notes + questions | ☐ | ☐ |  |  |
| trees | disjoint_set_union | notes + questions | ☐ | ☐ |  |  |
| graphs | graph_representation | notes + questions | ☐ | ☐ |  |  |
| graphs | bfs | notes + questions | ☐ | ☐ |  |  |
| graphs | dfs | notes + questions | ☐ | ☐ |  |  |
| graphs | topological_sort | notes + questions | ☐ | ☐ |  |  |
| graphs | cycle_detection | notes + questions | ☐ | ☐ |  |  |
| graphs | connectivity_scc | notes + questions | ☐ | ☐ |  |  |
| paradigms | backtracking | notes + questions | ☐ | ☐ |  |  |
| paradigms | greedy | notes + questions | ☐ | ☐ |  |  |
| graphs | dijkstra | notes + questions | ☐ | ☐ |  |  |
| graphs | bellman_ford | notes + questions | ☐ | ☐ |  |  |
| graphs | minimum_spanning_tree | notes + questions | ☐ | ☐ |  |  |
| paradigms | dp_fundamentals | notes + questions | ☐ | ☐ |  |  |
| graphs | floyd_warshall | notes + questions | ☐ | ☐ |  |  |
| paradigms | dp_classic | notes + questions | ☐ | ☐ |  |  |
| paradigms | string_matching | notes + questions | ☐ | ☐ |  |  |
| paradigms | complexity_classes | notes + questions | ☐ | ☐ |  |  |

## 13. Evaluation Results

### 13.1 Automated (RAGAs + custom), filled in during Phase 12

| Metric | Plain RAG | GraphRAG | Δ | p-value | Notes |
|---|---|---|---|---|---|
| Prerequisite Hit Rate (unnamed_prerequisite) | | | | | **headline** |
| Prerequisite Hit Rate (all) | | | | | |
| Faithfulness | | | | | |
| Answer relevancy | | | | | |
| Context precision | | | | | |
| Context recall | | | | | |
| Concept accuracy@1 | n/a | | | | |
| Off-topic decline accuracy | | | | | |
| Avg latency (s) / avg tokens | | | | | |

Run ID / date / models used: _TBD_

### 13.2 User study

| | Adaptive | Baseline |
|---|---|---|
| Participants (n) | | |
| Pre-test mean | | |
| Post-test mean | | |
| Normalized gain (mean ± sd) | | |
| Test / p-value / effect size | | |

### 13.3 Other evidence

- LLM proposal acceptance rate after human review: _TBD_
- Production smoke test results: _TBD_

---

## 14. Study Notes: What We Learned

> A running glossary and concept list for viva preparation. Claude Code adds entries as it uses new ideas.

| Topic | Plain-language explanation | Where it's used in Cognexa |
|---|---|---|
| GraphRAG | Retrieval guided by relationships in a knowledge graph, not just text similarity | app/tutor |
| Cypher variable-length path | `-[:PREREQUISITE_OF*1..2]->` matches chains of 1–2 edges | GraphRepository.get_prerequisites |
| DAG / topological order | Directed graph without cycles; an order where every prerequisite comes first | validate_graph.py, recommender R4/R5 |
| Server-Sent Events | One-way streaming over HTTP for token-by-token answers | /tutor/.../messages |
| Row Level Security | Postgres policies that restrict rows per user | supabase/migrations |
| Reciprocal Rank Fusion | Merges ranked lists from different retrievers | classifier fallback |
| Normalized learning gain | (post − pre) / (max − pre) | study analysis |
| CSS-variable theming | Colours are variables on `[data-theme]`; switching the attribute re-skins everything without re-rendering | globals.css, ThemeProvider |
| No-flash theme script | A tiny inline script sets `data-theme` before first paint so the wrong theme never flashes | theme-script.tsx |
| ASGI middleware | Code wrapping every request at the server-protocol level; used for request IDs | app/core/middleware.py |
| WCAG AA contrast | Text needs at least 4.5:1 against its background; checked by a unit test | src/test/contrast.test.ts |
| Health vs deep health | Liveness (cheap, no DB) vs readiness (pings dependencies) | /health, /health/deep |
| Unnamed-prerequisite test item | An eval question that describes only a symptom ("RecursionError at n = 5000") whose gold answer needs a prerequisite it never names (call_stack) | `data/subjects/dsa/eval/testset.jsonl`, validator rule |
| Matched pre/post forms | Two tests over the same concepts with the same difficulty profile and no shared items, so learning gain is not inflated by memorising questions | `questions/_study_sets.yaml` |
| Self-verifying content | Every code sample asserts its own claims and every `code_output` key is checked against real program output | `app/content/snippets.py`, `scripts/run_content_snippets.py` |
| JWKS | A public list of signing keys published by the auth server; the API verifies tokens with it without holding any secret | `app/auth/jwks.py`, `app/auth/tokens.py` |
| Open-redirect guard | Only same-site relative paths are accepted as the post-login destination, so a crafted link cannot send users to another site | `safeNext` in `src/lib/auth-schemas.ts` |
| Reduced motion | Users can ask the OS for less animation; the CSS removes durations and delays so content appears at once | `globals.css`, BUG-016 |
| Route prefetching | Next.js loads a linked page's code in the background; useful, but it adds that code to the current page's cost | DEC-024 |

---

## 15. Project Summary for the Final Report

_(Written in Phase 16: what was built, key results, limitations, future work.)_

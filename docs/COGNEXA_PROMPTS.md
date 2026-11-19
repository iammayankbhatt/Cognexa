# Cognexa — Claude Code Build Prompts

Paste these prompts into **Claude Code** one at a time, in order. Each prompt is one build phase. Together they build the whole Cognexa product: a GraphRAG DSA tutor with auth, quizzes, auto-grading, an adaptive recommender, dashboards, an admin console, usage limits, evaluation and free-tier deployment.

---

## How to use this pack

1. **Create an empty folder** called `cognexa`. Put `CLAUDE.md` and `progressfile.md` in the root, and this file and `PHASE0_SETUP.md` in `docs/`. Run `git init`.
2. **Do Phase 0 (manual setup) first.** It creates the free accounts and keys you'll need.
3. Open Claude Code in the `cognexa` folder. For each phase:
   - Paste the prompt. For big phases, ask Claude Code to **show its plan first** and approve it before it writes code.
   - Let it finish, **run the app yourself** and check the "Verify" list.
   - Make sure it did the Standard Wrap-up (progressfile.md updated plus small verified commits on `main`).
   - **Push, watch CI, and tag.** When the phase is done, you run `git push`, watch the CI run on GitHub, and once it is green tag the phase (`git tag -a v0.N -m "Phase N: <name>" && git push --tags`). A red CI is fixed before you start the next phase. Details in Appendix D.
   - Start a fresh session (`/clear`) before the next phase. CLAUDE.md and progressfile.md carry the context forward.
4. If something breaks, use the **Bug Fix prompt** (Appendix B). If you come back after a break, use the **Resume prompt** (Appendix A).
5. Don't skip phases or merge several into one prompt. Small phases with checks in between are how you keep bugs out.

> **A note on "no bugs":** No tool can guarantee zero bugs. This pack gets close by building in checks: every phase must pass lint, type checks, tests and a manual run before it counts as done. Phase 14 is a dedicated bug-hunt phase, and every bug found is logged in `progressfile.md`. You still have to click through each phase. Doing that is also your best preparation for the viva.

### Phase map

| # | Phase | Report link |
|---|---|---|
| 0 | Manual setup: accounts and keys | — |
| 1 | Monorepo scaffold, design system, CI | Obj. 4 |
| 2 | Databases: Postgres schema + Neo4j schema + DSA concept graph | Obj. 1 |
| 3 | Content: concept notes + question bank + eval test set | Obj. 1, 5 |
| 4 | Auth, roles, app shell, landing page, themes | Product |
| 5 | LLM provider layer, usage limits, cost metering, caching, guardrails | Product |
| 6 | GraphRAG pipeline + plain-RAG baseline + bounded agentic step | Obj. 2 |
| 7 | Tutor chat UI: streaming, history, "why this answer", feedback/reporting | Obj. 2 |
| 8 | Quiz engine, auto-grading, mastery model | Obj. 3 |
| 9 | Adaptive recommender + non-adaptive baseline + spaced review | Obj. 3, 5 |
| 10 | Progress dashboard, mastery graph, notes & revision sheets | Product |
| 11 | Admin console: graph editor, LLM-proposed tags + human review, moderation, analytics | Gap I |
| 12 | Evaluation: RAGAs harness + user-study mode + analysis | Obj. 5 |
| 13 | Hardening: security, performance, accessibility, observability, e2e | Product |
| 14 | Bug hunt + fresh-eyes review | Product |
| 15 | Deployment (free tiers) + keep-alive + production smoke test | Obj. 4 |
| 16 | Documentation, architecture diagrams, viva demo script | Report |

---

## Phase 0 — Manual setup (you do this, not Claude Code)

> **Detailed click-by-click instructions are in `docs/PHASE0_SETUP.md`.** The table below is a summary.

Create these free accounts. Store keys in a password manager. **Never paste keys into chat.** You'll put them in `.env` files and hosting dashboards.

| Service | What to create | You will need |
|---|---|---|
| GitHub | Repo `cognexa` (public repos get unlimited Actions minutes; private repos get a monthly free quota) | repo URL |
| Supabase | **Two** free projects: `cognexa-dev` and `cognexa-prod` (the free plan allows 2). In each: enable the `vector` extension; Auth → enable Email (with confirm) and Google provider | project URL, anon/publishable key, service-role/secret key, Postgres connection strings (direct + pooler) |
| Neo4j AuraDB | One **Free** instance (for production; local dev uses Docker) | URI (`neo4j+s://…`), username, password |
| Groq | API key from the Groq console (free tier, no card) | `GROQ_API_KEY` |
| Google AI Studio | Gemini API key (free tier) | `GEMINI_API_KEY` |
| Google Cloud Console | OAuth client (Web) for Supabase Google login. Redirect URI = the callback URL Supabase shows | client ID / secret, pasted into Supabase |
| Vercel | Hobby account, linked to GitHub | — |
| Render | Free account, linked to GitHub | — |
| Local machine | Docker Desktop, Node.js LTS, Python 3.12, `uv`, Git, Claude Code | — |

Free-tier facts the design accounts for:
- **Neo4j Aura Free** auto-pauses after 72 hours idle and is deleted if left paused too long. The fixes are a daily keep-alive ping plus the ability to re-seed from `concepts.yaml` at any time.
- **Supabase Free** pauses a project after about 7 days of low activity. The same keep-alive ping covers it.
- **Render Free** sleeps after 15 minutes idle and takes about a minute to wake. The frontend shows a "waking up" state and warms the API when the page loads.
- **LLM free tiers** are rate-limited and change often. That's why we have the provider fallback, caching and per-user quotas. Check your current limits in each provider's console. Gemini's free tier may use prompts to improve Google products, so send no personal data in prompts (questions only).

---

## Phase 1 — Scaffold, design system, CI

```text
Read CLAUDE.md and progressfile.md fully before doing anything. You are building Cognexa (see CLAUDE.md §1–§4). This is Phase 1: scaffold the monorepo, the design system and CI. Show me your plan first, then implement.

Tasks:
1. Create the repository layout exactly as in CLAUDE.md §4 (empty folders get a .gitkeep). Add a root .gitignore (Node, Python, .env*, .venv, .next, coverage, playwright reports) and a root README.md stub.
2. apps/api: FastAPI project managed by uv (Python 3.12). Include:
   - app/main.py with app factory, CORS (origins from env ALLOWED_ORIGINS), request-ID middleware, structured JSON logging, consistent error handler returning {error:{code,message,request_id}}.
   - app/core/config.py using pydantic-settings; every setting documented in apps/api/.env.example.
   - GET /health (cheap, no DB) and GET /health/deep (pings Postgres and Neo4j; returns per-dependency status and latency). For now deep health may report "not_configured" if env is missing. It must not crash.
   - Tooling: ruff (lint + format), mypy (strict on app/), pytest + pytest-asyncio + httpx. A first test for /health.
3. apps/web: Next.js (latest stable, App Router, TypeScript strict, src/ dir), Tailwind, shadcn/ui initialised, ESLint, Prettier, Vitest + Testing Library, Playwright installed (config only for now). Scripts: dev, build, start, lint, typecheck, test, e2e.
4. Design system (CLAUDE.md §6):
   - Implement the three themes (neon-noir default, titanium-dark, titanium-light) as CSS variables on [data-theme] and map them into Tailwind's theme (colors: bg, surface, surface-2, border, text, muted, primary, primary-fg, accent, success, warning, danger). Wire shadcn tokens to these variables.
   - Theme provider + switcher component (persists to localStorage for now; profile sync comes in Phase 4). No flash of wrong theme on load.
   - Fonts via next/font (Geist or Inter + JetBrains Mono).
   - Build a /design route (dev-only, hidden in production) showing every token, typography scale, buttons, inputs, cards, badges, tabs, dialogs, toasts, skeleton loaders, empty state and error state in all three themes. This is our visual reference and screenshot source.
   - Write the shared UI primitives we'll reuse: PageHeader, StatCard, EmptyState, ErrorState, LoadingSkeleton, MasteryBadge (low/mid/high colours), ConceptChip.
5. docker-compose.yml with neo4j:5 (APOC not required) and pgvector/pgvector:pg16, with healthchecks, named volumes and ports from .env.
6. .github/workflows/ci.yml: on push/PR run backend (uv sync, ruff, mypy, pytest with neo4j + pgvector service containers) and frontend (npm ci, lint, typecheck, test, build) as separate jobs, with caching.
7. Fill in README.md: what Cognexa is, the stack, and how to run locally.

Verify: `docker compose up -d` is healthy; the API starts and /health returns 200; the web dev server runs; /design looks polished in all 3 themes (take screenshots with Playwright and save them to docs/screenshots/phase1/); all lint/type/test/build commands pass; the CI workflow YAML is valid.

Finish with the Standard Wrap-up from CLAUDE.md §9. In progressfile.md also fill in the Tech Stack table with the exact versions installed.
```

---

## Phase 2 — Databases and the DSA concept graph

```text
Read CLAUDE.md and progressfile.md. Phase 2: database schemas and the DSA prerequisite knowledge graph (Report Objective 1). Plan first, then implement.

A. Concept graph source of truth: data/subjects/dsa/concepts.yaml
Create it from the concept list in docs/COGNEXA_PROMPTS.md → Appendix C (69 concepts, 8 clusters). For each concept include: id, name, cluster, difficulty (1–5), order_index (topological teaching order), description (1–2 sentences), aliases (alternative names students use), keywords (symptom words, e.g. call_stack → "stack overflow", "RecursionError", "maximum recursion depth", "segfault"), prerequisites (list of ids), related (list of ids). Keywords and aliases matter: they drive classification of "unnamed prerequisite" questions.
Add `subject: {id: dsa, name: "Data Structures & Algorithms"}` at the top.

B. scripts/validate_graph.py
Fails (non-zero exit, clear messages) if: duplicate ids; a reference to an unknown id; a cycle in prerequisites (print the cycle); a concept is its own prerequisite/related; an orphan (no prereqs AND nothing depends on it, except the designated roots); order_index violates prerequisite order. Prints stats: node count, edge counts, max depth, roots, leaves. Add it to CI.

C. Neo4j (apps/api/app/graph/)
- Schema: (:Subject {id,name}), (:Concept {id, subject_id, name, cluster, difficulty, order_index, description, aliases, keywords, status}), (:Chunk {id, concept_id, subject_id, kind, heading, text, order, reviewed})
- Relationships: (Subject)-[:HAS_CONCEPT]->(Concept); (A)-[:PREREQUISITE_OF {weight, source:'human'|'llm', status:'approved'|'proposed', rationale}]->(B) meaning A before B; (A)-[:RELATED_TO {weight, source, status}]->(B) (stored once, queried undirected); (Concept)-[:HAS_CHUNK]->(Chunk).
- Uniqueness constraints on Concept.id and Chunk.id, index on Concept.subject_id, plus a fulltext index on Concept name/aliases/keywords.
- A GraphRepository class (async) with typed methods: get_concept, list_concepts(subject), get_prerequisites(concept_id, depth), get_dependents(concept_id, depth), get_related(concept_id), get_subgraph(concept_ids, depth), get_chunks(concept_ids, kinds, limit), topological_order(subject), would_create_cycle(a,b), upsert_concept, upsert_edge, delete_edge. All queries parameterised (no string-built Cypher with user input).
- scripts/seed_neo4j.py: idempotent (MERGE), loads concepts.yaml (chunks come in Phase 3). Has a --wipe flag that asks for confirmation.

D. Postgres (supabase/migrations/)
Write SQL migrations (they must apply on Supabase AND on plain Postgres+pgvector in CI; create a test-only shim for the `auth` schema/auth.users so FKs work in CI). Tables (snake_case, uuid PKs, created_at/updated_at, subject_id where relevant):
- profiles (id = auth.users.id, display_name, role enum student|reviewer|admin default student, theme, study_group enum adaptive|baseline|none, onboarding_completed, quota_override jsonb)
- subjects, concepts (mirror of graph nodes for FKs and fast lookups: id text PK, subject_id, name, cluster, difficulty, order_index)
- content_chunks (id, concept_id, subject_id, kind, heading, text, embedding vector(<EMBEDDING_DIM>), reviewed). HNSW or ivfflat index on embedding. EMBEDDING_DIM comes from config; document how to change it.
- questions (id, concept_id, subject_id, type enum mcq|multi_select|true_false|code_output|short_answer, difficulty 1–3, prompt, code, options jsonb, answer jsonb, explanation, rubric jsonb, misconception_tag, diagnoses_prereq text null, status, source)
- quiz_sessions (user, mode enum concept|adaptive|review|diagnostic|pretest|posttest, concept_id null, started_at, submitted_at, score, max_score, time_limit_s), quiz_answers (session, question, response jsonb, is_correct, score 0–1, feedback, graded_by enum auto|llm, time_ms)
- mastery (user_id, concept_id, score 0–1, attempts, correct, last_practiced_at, next_review_at, ease, PK(user_id, concept_id))
- chat_threads (user, title, subject_id, archived), chat_messages (thread, role, content, mode enum graphrag|plain_rag, matched_concepts jsonb, retrieval_trace jsonb, provider, model, tokens_in, tokens_out, latency_ms, cached bool)
- message_feedback (message, user, rating -1|1 null, report_reason enum incorrect|incomplete|off_topic|harmful|other null, comment, status enum open|reviewing|resolved|dismissed, resolved_by, resolution_note)
- usage_daily (user_id, date, ai_requests, tokens_in, tokens_out, est_cost_usd, PK(user_id,date)), global_usage_daily (date PK, ai_requests, tokens_in, tokens_out)
- response_cache (key_hash PK, payload jsonb, concept_ids, created_at, expires_at, hits, invalidated)
- notes (user, concept_id, body, bookmarked), revision_sheets (user, concept_ids, content, created_at)
- recommendations_log (user, concept_id, reason_code, reason_text, path jsonb, study_group, shown_at, clicked_at, completed_at)
- graph_proposals (type enum add_edge|remove_edge|tag_chunk|new_concept, payload jsonb, rationale, confidence, status enum pending|approved|rejected, proposed_by enum llm|user, reviewer_id, decided_at, note)
- study_settings (singleton: enabled, assignment enum random|alternate, pretest_set_id, posttest_set_id, started_at), eval_runs, eval_results
- app_settings (key PK, value jsonb) — holds quota defaults and the global cap, editable by admin
- audit_log (actor, action, target, details jsonb)
Enable RLS on every table. Policies: users can read/write only their own rows where that makes sense; nothing for anon. The backend uses the service role. Add a trigger that creates a profiles row on auth.users insert.
- apps/api/app/db/: async engine/session (asyncpg, pooler-safe settings per CLAUDE.md rule 6), table definitions (SQLAlchemy Core or ORM, your choice, but be consistent), repositories per domain.
- scripts/seed_postgres.py: idempotent upsert of subjects + concepts mirror from concepts.yaml, plus default app_settings: student daily ai_requests=40, per_minute=6, max_input_chars=2000, max_output_tokens=900, global_daily_cap=1500, reviewer/admin x5.

E. Tests
Unit tests for the validator (including a deliberately cyclic fixture). Integration tests (docker neo4j + postgres) for GraphRepository methods, especially get_prerequisites depth, topological_order and would_create_cycle. Migration test: apply all migrations on a fresh DB.

Verify: validate_graph passes on the real file and fails on a cyclic fixture; seeds run twice without duplicates; in Neo4j Browser `MATCH (c:Concept {id:'call_stack'})-[:PREREQUISITE_OF*1..3]->(d) RETURN c,d` shows recursion and tree traversals; all tests pass. Paste the graph stats into progressfile.md.

Finish with the Standard Wrap-up.
```

---

## Phase 3 — Content: concept notes, question bank, eval test set

> This phase is mostly writing. Claude Code drafts it, and **you must review it**, because examiners will check accuracy. Every file starts with `reviewed: false`. You set it to true after checking.

```text
Read CLAUDE.md and progressfile.md. Phase 3: write the learning content for all 69 DSA concepts in data/subjects/dsa/concepts.yaml, the question bank, and the evaluation test set. Quality matters more than speed. Work ONE CLUSTER AT A TIME (foundations, complexity, linear, searching_hashing, sorting, trees, graphs, paradigms). After each cluster, run the validators and commit, then continue to the next cluster in this same session. If the context gets long, stop after a cluster, do the wrap-up, and tell me which cluster is next.

1. Concept notes: data/subjects/dsa/content/<concept_id>.md
Frontmatter: id, name, cluster, reviewed: false, sources (textbook chapter references, e.g. CLRS/Sedgewick chapter names, no copied text).
Body uses EXACTLY these H2 sections (each becomes a retrievable Chunk with `kind`):
## Overview (kind: overview)
## Intuition (kind: intuition) — an everyday analogy
## How It Works (kind: mechanism) — step by step
## Worked Example (kind: example) — traced by hand, with a small ASCII diagram where helpful
## Code (kind: code) — idiomatic Python AND C++, commented, correct, runnable
## Complexity (kind: complexity) — time/space, best/avg/worst, with why
## Common Mistakes & Misconceptions (kind: pitfalls) — the symptoms students would describe (error messages, wrong outputs)
## Builds On (kind: prerequisites) — explicitly explain HOW each prerequisite is used by this concept. This section is crucial for GraphRAG answers.
## Leads To (kind: next) — what this enables
## Check Yourself (kind: self_check) — 3 short questions with hidden answers
Write all prose originally (no copying from books/websites). Target 600–1200 words per concept. Code must actually run: put every Python snippet under tests/content_snippets via an extraction script and execute them in CI (C++: compile check if g++ is available, otherwise skip with a note).

2. Question bank: data/subjects/dsa/questions/<concept_id>.yaml
At least 8 questions per concept: at least 4 mcq, 1 multi_select, 1 true_false, 1 code_output, 1 short_answer, spread across difficulty 1–3. Each has: id (stable, e.g. call_stack-q03), type, difficulty, prompt, optional code, options, answer, explanation (why correct AND why each distractor is wrong), misconception_tag, and diagnoses_prereq (the prerequisite concept id a wrong answer suggests is weak, or null). Short answers include a rubric: {key_points:[...], max_score:1, partial_credit:true}. Distractors must be plausible misconceptions, not silly. Also create data/subjects/dsa/questions/_study_sets.yaml with two parallel 20-question forms (pretest_A, posttest_B) covering the same concepts at matched difficulty, for the user study.

3. Evaluation test set: data/subjects/dsa/eval/testset.jsonl (at least 80 items)
Each line: {id, question, category, gold_concepts:[...], gold_prerequisites:[...], reference_answer}. Categories with minimum counts:
- direct (20): names the concept explicitly
- unnamed_prerequisite (25): describes a symptom without naming the needed prerequisite, e.g. "my recursive fibonacci crashes with RecursionError for n=5000, why?" → gold_prerequisites [call_stack]. THIS CATEGORY IS THE PROJECT'S CENTRAL CLAIM.
- multi_concept (15): compares or combines concepts
- misconception (12): the student states something wrong
- off_topic (8): not DSA (the tutor should decline politely)

4. Tooling
- scripts/validate_content.py: every concept has a content file with all required sections; every question file passes schema validation (pydantic), answers reference valid options, there are ≥8 questions with the type mix above, ids are unique, diagnoses_prereq is a real prerequisite of that concept (or null), and the testset references valid concepts. Prints a coverage table. Add to CI.
- Extend seed_neo4j.py to create Chunk nodes from the H2 sections; extend seed_postgres.py to load questions and content_chunks text; create scripts/seed_vectors.py to embed content_chunks with the embedding provider (batching, retry, resumable, skips unchanged chunks via content hash). If the Phase 5 provider layer doesn't exist yet, write seed_vectors.py against a small interface and finish wiring it in Phase 5. Note this in progressfile.md.

Verify: validate_content passes; all Python snippets execute; the seeds load everything; spot-check 5 random concepts and 10 random questions for correctness and report what you checked. Add a "Content Review Checklist" section to progressfile.md listing every concept with reviewed status so the team can tick them off.

Finish with the Standard Wrap-up.
```

---

## Phase 4 — Auth, roles, app shell, landing page, themes

```text
Read CLAUDE.md and progressfile.md. Phase 4: authentication, authorisation, the application shell, and the public pages. Plan first.

Backend:
1. JWT verification dependency: verify Supabase access tokens using the project's JWKS endpoint (asymmetric signing keys, cached with refresh); support the legacy HS256 JWT secret only if configured. Check current Supabase docs for the exact JWKS URL and claims. Extract user id, email, role (from profiles table, cached briefly). Dependencies: get_current_user, require_role("reviewer"|"admin").
2. Endpoints: GET /me (profile + role + theme + study_group + today's usage), PATCH /me (display_name, theme), POST /me/onboarding-complete. Admin: GET /admin/users (search, paginate), PATCH /admin/users/{id} (role, quota_override, study_group). Every admin action writes audit_log.
3. Tests with signed test tokens (generate a local RSA key in tests and point JWKS at a stub).

Frontend:
4. Supabase SSR auth (@supabase/ssr): sign up (email+password, confirmation email), sign in, Google OAuth, forgot/reset password, sign out, auth callback route, middleware protecting /app/* and /admin/* (admin also checks role via /me). Friendly errors and loading states on every form (react-hook-form + zod).
5. API client: typed fetch wrapper that attaches the access token, refreshes on 401 once, maps error JSON to toasts, and has a "waking up the server" banner if the first request takes over 3 s (Render free cold start). Call /health on app load to warm the API.
6. App shell (/app): collapsible sidebar (Dashboard, Tutor, Learn, Quizzes, Review, Notes, Settings; Admin section only for reviewer/admin), top bar with search (concepts), theme switcher (synced to profile), usage meter (today's AI requests vs quota), and user menu. Mobile responsive with a drawer.
7. Onboarding flow after first login: welcome → pick experience level → short 10-question diagnostic quiz (wired in Phase 8; for now a placeholder screen, clearly marked, that Phase 8 must replace) → land on dashboard.
8. Public pages, designed to impress at a viva:
   - Landing (/): hero with an animated, subtle concept-graph background (canvas or SVG, respects reduced motion), tagline, "the failure case" section (student asks about recursion overflow → plain RAG misses it → Cognexa walks to Call Stack, shown as an animated mini-graph), how-it-works 5-step pipeline (Ask → Classify → Traverse → Gather → Answer), features grid, a "Plain RAG vs Cognexa" comparison, and a CTA.
   - /how-it-works: detailed explainer of GraphRAG, the knowledge graph (live read-only mini graph from the API), the recommender, and the evaluation method.
   - /about (team, guide, university, project ID), /privacy (incl. that LLM providers process questions and that Gemini's free tier may use prompts for product improvement; we don't send names or emails to LLMs), /terms.
9. Settings page: profile, theme picker with live previews of all 3 themes, data export (JSON of own data), delete account (with confirmation; backend endpoint deletes the user's rows and the auth user via the admin API).

Verify: the full auth cycle works locally against cognexa-dev (sign up → confirm → sign in → Google → reset → sign out); a student cannot reach /admin (UI and API both return 403); theme persists across devices via profile; Lighthouse on landing ≥ 90 for performance/accessibility/best practices; Playwright e2e covers sign-in and route protection; screenshots of landing in all themes are saved to docs/screenshots/phase4/.

Finish with the Standard Wrap-up.
```

---

## Phase 5 — LLM provider layer, usage limits, cost metering, caching, guardrails

```text
Read CLAUDE.md and progressfile.md. Phase 5: the AI infrastructure every later feature depends on. Plan first.

1. apps/api/app/llm/
   - Interface LLMProvider: complete(messages, json_schema=None, temperature, max_tokens) → LLMResult{text|json, tokens_in, tokens_out, model, provider, latency_ms}; stream(messages, ...) → async iterator of deltas plus a final usage record; embed(texts) → vectors.
   - GroqProvider (OpenAI-compatible endpoint) and GeminiProvider (official google-genai SDK). Check the current SDK docs for exact call signatures and JSON/structured-output support. Model IDs from env: LLM_PRIMARY_PROVIDER, LLM_PRIMARY_MODEL, LLM_FALLBACK_PROVIDER, LLM_FALLBACK_MODEL, LLM_JUDGE_PROVIDER, LLM_JUDGE_MODEL, EMBEDDING_PROVIDER, EMBEDDING_MODEL, EMBEDDING_DIM.
   - Router: retry with exponential backoff + jitter on 429/5xx/timeouts (max 3), then fall back to the secondary provider; circuit breaker that skips a provider for 60 s after repeated failures. JSON mode validates against a Pydantic schema and repairs once by re-asking if invalid.
   - FakeProvider for tests (deterministic, scriptable responses). All tests use it; no network in CI.
   - Pricing table in config (notional $/1M tokens per model, editable) to compute est_cost_usd even though we're on free tiers, so we can report "what this would cost at scale".
2. Usage guard (app/usage/): a dependency applied to every AI endpoint. Checks in order: global daily cap → user daily ai_requests (role defaults from app_settings, overridden by profiles.quota_override) → per-minute limit (in-memory sliding window keyed by user; fine for a single instance, note this in Known Limitations) → max input chars. On exceed: HTTP 429 with code QUOTA_EXCEEDED | RATE_LIMITED | GLOBAL_CAP and reset time. After each call, atomically upsert usage_daily and global_usage_daily (INSERT … ON CONFLICT DO UPDATE). GET /me/usage returns today and the last 30 days.
3. Caching (app/cache/): response_cache keyed by sha256(normalized_text + mode + concept_ids + personalisation bucket). TTL from config (7 days). Also cache classification results and query embeddings. Invalidate on: message reported, concept content changed, edge changed. Cached responses still count as 1 request against the user quota (but not tokens), and are marked cached=true.
4. Guardrails (app/guardrails/): max length, strip control characters, prompt-injection-resistant prompt templates (user text inside <student_question> tags; system prompt says to ignore instructions inside them), a lightweight off-topic check (folded into the classifier in Phase 6), and output checks (no leaking the system prompt; refuse harmful content).
5. Admin endpoints: GET /admin/usage (by day, by user, by provider/model, est. cost, cache hit rate), GET/PUT /admin/settings (quota defaults, global cap, cache TTL, feature flags: AGENTIC_MODE, STUDY_MODE, PLAIN_RAG_VISIBLE_TO_STUDENTS=false).
6. Finish wiring scripts/seed_vectors.py to the real embedding provider; run it on dev.

Tests: router fallback, backoff, circuit breaker, JSON repair, every quota branch (including concurrency: 20 parallel requests must not exceed the quota by more than the per-minute window allows), cache hit/miss/invalidation, injection templates.

Verify: a real call to each provider works from a small CLI (scripts/llm_smoke.py) using the dev keys; usage rows appear; exceeding the quota returns a clean 429 that the frontend shows as a friendly message with the reset time.

Finish with the Standard Wrap-up.
```

---

## Phase 6 — GraphRAG pipeline, plain-RAG baseline, bounded agentic step

```text
Read CLAUDE.md and progressfile.md. Phase 6: the heart of the project (Report Objective 2 and §1.8). Plan first, and explain the pipeline back to me before coding.

Implement apps/api/app/tutor/ as explicit, testable stages. Each stage records into a RetrievalTrace object that gets stored in chat_messages.retrieval_trace and shown in the UI.

Stage 1 — Classify (zero-shot, LLM)
- Input: the question + the last 4 turns of the thread (for follow-ups like "why?") + the concept catalogue (id, name, short description, aliases, keywords; keep it compact and cache the formatted catalogue).
- Output (JSON schema): {is_on_topic: bool, concepts: [{id, confidence 0–1, reason}], intent: explain|debug|compare|example|complexity|other}. Allow up to 3 concepts.
- Hybrid fallback: if max confidence < CLASSIFY_THRESHOLD (0.55, configurable) or the JSON is invalid, also run (a) the Neo4j fulltext index over name/aliases/keywords and (b) embedding similarity over concept descriptions, then merge with reciprocal-rank fusion. Record which path was used.
- Off-topic → a polite decline that suggests DSA topics; costs no further LLM calls.

Stage 2 — Traverse (Cypher)
- For each matched concept: prerequisites up to depth 2 (PREREQUISITE_OF reversed), related depth 1, approved edges only.
- Personalise: load the user's mastery; mark each prerequisite as weak (score < 0.6 or never practised). Rank: matched concept first, then weak prerequisites (nearest first), then other prerequisites, then related.
- Record the exact paths (list of edges) for explainability.

Stage 3 — Gather
- Fetch chunks: for the matched concept, kinds chosen by intent (debug → pitfalls, mechanism, prerequisites; complexity → complexity; example → example, code; explain → overview, intuition, mechanism, prerequisites). For prerequisites/related: overview + pitfalls.
- Token-budgeted context builder (CONTEXT_TOKEN_BUDGET, default 3000): fill in rank order; each chunk labelled [concept_id/kind].

Stage 4 — Answer (streaming)
- System prompt: you are Cognexa, a patient DSA tutor; answer ONLY from the provided context; if the context doesn't cover it, say so and suggest the closest concept; when a weak prerequisite is relevant, explicitly connect it ("This happens because of how the call stack works — each recursive call adds a frame…") and suggest reviewing it; cite concepts inline as [[concept_id]]; use short sections, code blocks and complexity notes where useful; end with 2 suggested follow-up questions in a machine-readable trailer.
- Parse [[concept_id]] citations into links for the UI; strip the trailer into structured follow-ups.

Stage 5 — Bounded agentic step (justifies "Towards Agentic GraphRAG"; behind AGENTIC_MODE flag, default on)
- After Stage 2, a small controller LLM call (JSON) chooses ONE action: answer_now | ask_diagnostic (ask the student one quick check question about the most suspicious weak prerequisite before answering, e.g. "Quick check: what happens to memory each time a function calls itself?") | expand_traversal (depth 3 if context is thin). At most 2 controller steps per turn, never loops, and everything is recorded in the trace. A student reply to a diagnostic question continues the same turn's context.

Baseline — plain RAG (mode=plain_rag)
- Embed the question → top-k (k=6) pgvector cosine search over the SAME content_chunks → same answer prompt minus the graph/prerequisite instructions. Same token budget. Used by evaluation and by admins in a comparison view; hidden from students unless the flag allows.

API
- POST /tutor/threads, GET /tutor/threads (paginated), GET/PATCH/DELETE /tutor/threads/{id}
- POST /tutor/threads/{id}/messages → Server-Sent Events stream: events `trace` (classification + traversal summary, sent before tokens so the UI can show "Looking at: Recursion ← Call Stack"), `token`, `citation`, `followups`, `done` (message id, usage), `error`. Supports client disconnect (save the partial answer, marked truncated).
- POST /tutor/messages/{id}/regenerate, POST /tutor/compare (admin/reviewer: runs both modes on one question and returns both answers + traces).
- Persist every message with trace, provider, model, tokens, latency, cached flag. Auto-title new threads from the first question (cheap LLM call, or a heuristic fallback).

Tests (FakeProvider + integration graph):
- The canonical failure case: "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?" → graphrag retrieval includes call_stack chunks even though the question never says "stack"; the plain_rag result is recorded for comparison (assert graphrag ⊇ call_stack; do not assert plain_rag fails).
- Classifier fallback path, off-topic path, multi-concept question, token budget respected, personalisation ranks weak prerequisites first, the agentic controller never exceeds 2 steps, SSE event order, disconnect handling.

Verify: run 10 questions from testset.jsonl through both modes with real providers on dev and save the outputs to evaluation/reports/phase6_smoke.md with traces; review them with me.

Finish with the Standard Wrap-up.
```

---

## Phase 7 — Tutor chat UI

```text
Read CLAUDE.md and progressfile.md. Phase 7: the Tutor experience in the web app. It must feel as polished as a commercial AI chat product. Plan first.

1. /app/tutor layout: left panel thread list (search, new chat, rename inline, archive, delete with undo toast, grouped by Today/Yesterday/Last 7 days/Older); centre chat; right collapsible "Why this answer?" panel.
2. Chat: streaming rendering via SSE (fetch + ReadableStream; handle reconnect/abort), markdown with code highlighting + copy buttons + KaTeX, [[concept_id]] citations rendered as ConceptChips that open the concept page, suggested follow-ups as clickable chips, stop-generating button, regenerate, edit-and-resend the last user message, keyboard shortcuts (Enter send, Shift+Enter newline, Esc stop), character counter vs max input, auto-scroll that stops if the user scrolls up.
3. Live trace: as soon as the `trace` event arrives, show a compact animated strip ("Matched: Recursion (0.86) → walking prerequisites → Call Stack ⚠ weak"), then the answer.
4. "Why this answer?" panel: matched concepts with confidence and classification path (LLM / fallback), a mini Cytoscape graph of the traversed subgraph (matched node highlighted, weak prerequisites outlined in --danger, edge labels), the list of chunks used (concept/kind, expandable), the agentic action taken, and the model/provider/latency/tokens/cached flags.
5. Diagnostic question UX (agentic step): render it as a distinct "Quick check" card with an input; the answer continues the turn.
6. Feedback: thumbs up/down on every assistant message; "Report answer" dialog (reason enum + optional comment) → POST /tutor/messages/{id}/feedback; show "Thanks — a reviewer will check this". A reported message shows a subtle flag.
7. Empty state: starter prompts (including the recursion overflow example) and "Continue learning: <recommended concept>" (wired fully in Phase 9; for now use topological-next as a temporary rule and log the TODO in progressfile.md for Phase 9).
8. Errors: quota exceeded (friendly card with reset time + link to Review/Quizzes, which don't need AI), provider down (retry button), cold start (waking-up banner), network loss.
9. Admin/reviewer only: a "Compare with plain RAG" toggle that calls /tutor/compare and shows the two answers side by side with both traces. This is the live demo of the project's central claim.
10. Accessibility: aria-live for streaming, focus management, full keyboard use.

Tests: Vitest for the SSE parser, citation parser and follow-up trailer parser; Playwright e2e (with the backend using FakeProvider via an env flag) for: send message → see trace → see answer → open why-panel → report answer → thread persists after reload.

Verify: run it against real providers on dev; record a short screen capture or a screenshot sequence into docs/screenshots/phase7/.

Finish with the Standard Wrap-up.
```

---

## Phase 8 — Quiz engine, auto-grading, mastery model

```text
Read CLAUDE.md and progressfile.md. Phase 8: quizzes, grading and mastery (feeds Report Objective 3). Plan first.

Backend (apps/api/app/quiz/ and app/mastery/):
1. Quiz modes: concept (pick a concept, 5–10 questions), adaptive (questions on recommended/weak concepts, difficulty matched to mastery: <0.4 → difficulty 1, 0.4–0.75 → 2, >0.75 → 3), review (due items from spaced review, Phase 9), diagnostic (onboarding: 10 questions spread across foundation and core concepts), pretest/posttest (study sets, Phase 12). Avoid repeating questions seen in the last 7 days when possible.
2. Endpoints: POST /quiz/sessions {mode, concept_id?, count?, timed?} → session with questions (answers NOT included); POST /quiz/sessions/{id}/answers (one at a time, supports immediate-feedback mode) or POST /quiz/sessions/{id}/submit (all at once, exam mode); GET /quiz/sessions/{id} (results after submit), GET /quiz/history.
3. Auto-grading:
   - mcq / true_false: exact match. multi_select: partial credit = max(0, (correct_chosen − wrong_chosen) / total_correct). code_output: normalise whitespace/case/trailing newlines, then exact match.
   - short_answer: LLM grader (judge model, JSON schema {score 0–1, matched_points[], missing_points[], feedback}) against the rubric, temperature 0, goes through the usage guard (counts as 1 request), result cached by (question_id, normalized answer). If the LLM is unavailable: mark "pending", grade on retry, never block quiz submission.
   - Every answer stores feedback: the explanation + (if wrong) the misconception and the diagnoses_prereq concept ("This often means Call Stack needs review").
   - Server-side timing; reject answers after the time limit in timed mode.
4. Mastery update (rule-based, documented in docs/ARCHITECTURE.md): for each graded answer on concept c, w = {1:0.8, 2:1.0, 3:1.2}[difficulty]; score_c ← clamp(score_c + 0.3·w·(result − score_c)). If result < 0.5 and diagnoses_prereq = p, apply a small negative signal to p: score_p ← score_p − 0.05 (floor 0). Update attempts, correct, last_practiced_at. Time decay applied at read time: effective = score · 0.98^(days since last practised / 7). Mastery bands: <0.4 weak, 0.4–0.75 developing, >0.75 strong. Keep these constants in config.
5. Question-asking signal for the recommender: log the matched concepts of each tutor question into a lightweight table/view (concept_interest: user, concept, asked_at) so Phase 9 can use "questions asked", as the report requires.

Frontend:
6. /app/quizzes: start-quiz cards (by concept with search/filter by cluster; adaptive "Smart quiz"; review due count), history table with scores and trends.
7. Quiz player: one question per screen, progress bar, optional timer, code blocks highlighted, multi-select checkboxes, short-answer textarea, flag-for-later, keyboard navigation (1–4 to select, Enter to confirm), immediate-feedback mode vs exam mode. Results screen: score ring, per-concept breakdown, each question's explanation, "weak prerequisite detected → Learn it / Ask the tutor about it" actions, retry wrong ones.
8. Replace the Phase 4 onboarding placeholder with the real diagnostic quiz, which seeds initial mastery.
9. /app/learn and /app/learn/[conceptId]: concept library grouped by cluster with mastery badges and lock hints ("Recommended after: Recursion"); the concept page renders the markdown content (all sections, tabbed Python/C++ code), its prerequisites/leads-to as chips, "Ask the tutor about this", "Practice this concept", and bookmark/note buttons (notes UI in Phase 10).

Tests: grading for every type including partial credit and edge cases (empty answers, duplicate selections); mastery update math (table-driven tests); the LLM grader with FakeProvider including the pending/retry path; e2e: take a concept quiz end to end and see mastery change on the concept page.

Verify: take the diagnostic as a new user and confirm mastery rows are created; take a short-answer question with the real judge model on dev.

Finish with the Standard Wrap-up.
```

---

## Phase 9 — Adaptive recommender, non-adaptive baseline, spaced review

```text
Read CLAUDE.md and progressfile.md. Phase 9: the rule-based adaptive recommendation engine that reuses the same graph (Report Objective 3, §1.8), its non-adaptive baseline for the user study (Objective 5), and spaced review. Plan first.

1. apps/api/app/recommender/ — pure, deterministic, fully unit-testable functions over (graph, mastery, interest signals). Rules, in priority order:
   R1 Root-cause repair: find weak concepts W (effective mastery < 0.6 with ≥ 2 attempts, OR asked about ≥ 3 times in the last 7 days with mastery < 0.75). For the most important W (most recent failures, then most asked), walk PREREQUISITE_OF edges backward (BFS). Recommend the "frontier gap": the unmastered prerequisite (< 0.6 or unpractised) that has no unmastered prerequisites itself, i.e. the deepest real gap. Reason: "You've struggled with Tree Traversals; it builds on Recursion, which builds on Call Stack — start there."
   R2 If all of W's prerequisites are mastered → recommend W itself for focused review.
   R3 Due review: items with next_review_at ≤ now.
   R4 Forward progress: the next "unlocked" concept (all prerequisites ≥ 0.6, itself < 0.75), lowest order_index first.
   R5 Fallback for brand-new users: the first concept in topological order not yet strong.
   Output: up to 3 recommendations, each {concept_id, rule (R1–R5), reason_text, path (edge list), suggested_action: learn|practice|review}.
2. Baseline (non-adaptive): fixed syllabus order. Recommend the next concept by order_index that is not yet marked complete (completed = took a concept quiz with ≥ 60%), ignoring mastery and questions asked. Same output shape, with rule = BASELINE.
3. Group routing: if STUDY_MODE is on and profile.study_group = baseline → serve the baseline everywhere (dashboard, tutor empty state, post-quiz screens); adaptive → the rule engine; none → the rule engine. Log every recommendation shown/clicked/completed in recommendations_log (needed for the study analysis).
4. Spaced review: after each concept quiz, schedule next_review_at with an SM-2-lite rule (interval days 1 → 3 → 7 → 14 → 30 on success, reset to 1 on failure; ease stored in mastery.ease). GET /review/due returns due concepts with 3–5 questions each; this works without AI, so it stays usable when the LLM quota is exhausted.
5. Endpoints: GET /recommendations, POST /recommendations/{id}/click, GET /review/due.
6. Frontend: a "Next best step" card (reason text + a mini path graph) on the dashboard, the tutor empty state (replace the Phase 7 temporary rule) and the quiz results screen; /app/review page with due items and streak.

Tests: table-driven unit tests over a small synthetic graph covering every rule, ties, cycles impossible, the empty-mastery user, and the canonical chain function→call_stack→recursion→tree traversal (failing tree traversal + weak recursion + weak call_stack → recommends call_stack). Baseline tests. Logging tests.

Verify: create two test users on dev, one per study group; simulate quiz results; confirm the recommendations differ as expected and are logged.

Finish with the Standard Wrap-up.
```

---

## Phase 10 — Progress dashboard, mastery graph, notes & revision sheets

```text
Read CLAUDE.md and progressfile.md. Phase 10: the progress dashboard and the learner-facing graph, plus notes. This is a key presentation screen; make it beautiful. Plan first.

1. Backend: GET /dashboard (one call): overall mastery %, concepts by band, streak (days with any quiz/review activity), time-on-task estimate, quizzes this week, accuracy trend (last 30 days), per-cluster mastery, recent activity feed, top 3 weak concepts with suggested prerequisite, recommendations, review due count, today's AI usage. GET /graph/mastery: all concepts + approved edges + the user's effective mastery per node.
2. /app/dashboard: greeting + Next best step card; stat cards; accuracy trend line chart and per-cluster radar or bar chart (Recharts, themed); weak concepts list with "fix the root cause" buttons; activity timeline; review due widget; usage meter.
3. /app/graph "Knowledge Map": a full-screen Cytoscape DAG (dagre, top-to-bottom), nodes coloured by mastery band, size by difficulty, cluster grouping or filter, hover tooltip (mastery, attempts, last practised), click → side drawer with the concept summary + actions (learn, practice, ask tutor). A "Show my path" toggle highlights the current recommendation path. Smooth zoom/pan, a legend, and export as PNG (for the report!). Must perform well with 69 nodes on a laptop.
4. Notes: per-concept notes (markdown editor with preview) and bookmarks; /app/notes lists them with search and cluster filter.
5. Revision sheets (personalised study notes, the NotebookLM-like feature, grounded in OUR graph): POST /revision-sheets {concept_ids? default = weak concepts} → the LLM composes a 1–2 page revision sheet from those concepts' chunks + their weak prerequisites (through the usage guard; GraphRAG-grounded with citations). Save it; view it; export as Markdown and print-friendly PDF (browser print stylesheet, no paid service).
6. Empty states for brand-new users that guide them to the diagnostic.

Tests: dashboard aggregation queries (with seeded fixtures), graph endpoint shape, notes CRUD with ownership checks (user A can't read user B's notes, at both API and RLS level), revision sheet with FakeProvider; e2e: dashboard renders for a seeded user, knowledge map opens the drawer.

Verify: screenshots of the dashboard and knowledge map in all 3 themes → docs/screenshots/phase10/.

Finish with the Standard Wrap-up.
```

---

## Phase 11 — Admin console: graph editor, LLM-proposed tags with human review, moderation, analytics

```text
Read CLAUDE.md and progressfile.md. Phase 11: the reviewer/admin console. It implements the report's semi-automated graph building ("an LLM proposes tags and a human verifies them", Gap I). Plan first.

Routes under /admin (reviewer: graph/content/moderation; admin: everything):
1. Overview: users count, DAU/WAU, AI requests today vs global cap, cache hit rate, est. cost, open reports, pending proposals, last eval run.
2. Graph editor: the interactive Cytoscape graph plus a table view. Create/edit concepts (all fields), add/remove PREREQUISITE_OF and RELATED_TO edges with rationale. The backend rejects edges that would create a cycle (would_create_cycle) and the UI explains why. Every change writes audit_log, updates the Postgres concepts mirror, and invalidates affected cache entries. "Export to concepts.yaml" button (downloads YAML so changes can be committed back to git).
3. LLM proposals pipeline:
   a. "Suggest edges" for a concept: the LLM reviews the concept + candidates and proposes missing prerequisite/related edges with rationale + confidence → graph_proposals (pending).
   b. Document ingestion: upload a PDF/Markdown/TXT of lecture notes (pypdf for PDF text; size limit 10 MB; text-based PDFs only, show a clear message for scanned ones). The text is split into sections/chunks; for each chunk the LLM proposes {concept_id, kind, confidence, rationale} or "new concept?" → proposals.
   c. Review queue: filter by type/confidence; side-by-side view (proposal, rationale, affected subgraph preview); approve (optionally edit first) / reject with note; bulk approve above a confidence threshold with a confirmation. Approved chunks become Chunk nodes + content_chunks (embedded) with source=llm, reviewed=true; approved edges are written with source=llm, status=approved.
   d. Track proposal acceptance rate (useful evidence for the report: "LLM proposals accepted X% after human review").
4. Content & question bank editor: edit concept chunks (markdown with preview) and questions (form per type with validation, preview as the student sees it), mark reviewed, deactivate a question. Show question stats (attempts, % correct, discrimination: flag questions everyone gets right/wrong).
5. Moderation queue: reported answers with the full message, trace and user comment; actions: resolve (with note), dismiss, "fix content" (jump to the concept chunk), invalidate cache for that question. Thumbs-down analytics by concept.
6. Users: search, role change, quota override, study group, disable account; view a user's usage (not their chat contents unless reported — note the privacy policy).
7. Usage & cost: charts by day/provider/model, top users, cache hit rate, failures/fallbacks count, with CSV export.
8. Settings: quotas, global cap, cache TTL, feature flags (AGENTIC_MODE, STUDY_MODE, PLAIN_RAG_VISIBLE_TO_STUDENTS).

Tests: role enforcement on every admin endpoint (student → 403), the cycle rejection path, proposal approve/reject transactions (a graph write + Postgres write either both succeed or the operation reports partial failure and is retryable — document the approach), PDF ingestion with a fixture PDF, question editor validation, audit_log entries.

Verify: ingest a real 5–10 page DSA notes PDF on dev, review the proposals, approve some, and confirm the tutor now cites the new chunks.

Finish with the Standard Wrap-up.
```

---

## Phase 12 — Evaluation: RAGAs harness and user-study mode

```text
Read CLAUDE.md and progressfile.md. Phase 12: evaluation, which provides the evidence for the report (Objective 5, §1.9, RAGAs [10]). Plan first.

A. Automated retrieval/answer evaluation (evaluation/, offline, not deployed)
1. evaluation/ragas_eval.py: runs every item in data/subjects/dsa/eval/testset.jsonl through BOTH modes (calling the backend pipeline functions directly, or the /tutor/compare endpoint) with caching disabled, rate-limit aware (sleeps on 429, resumable checkpoints), and saves raw outputs (question, answer, contexts, trace) to evaluation/reports/<run_id>/raw.jsonl.
2. Metrics:
   - RAGAs (check the installed version's API; configure it to use our free judge model through its LLM/embedding wrappers): faithfulness, answer relevancy, context precision, context recall (using reference_answer).
   - Custom (our central claim): Prerequisite Hit Rate = fraction of items where the retrieved contexts include ≥1 chunk from each gold_prerequisite; Concept Accuracy@k for classification; Off-topic decline accuracy; avg latency; avg tokens.
   - Break everything down by category; unnamed_prerequisite is the headline row.
3. Statistics: paired comparison per metric (Wilcoxon signed-rank) with effect size and 95% bootstrap CIs. Be honest: report whatever the numbers say.
4. Output evaluation/reports/<run_id>/report.md (tables + charts as PNG via matplotlib) and push a summary into eval_runs/eval_results so the admin console shows it (add an /admin/evaluation page: latest run, metric table by mode and category, drill down to individual items with both answers side by side).
5. A GitHub Actions workflow_dispatch job (manual only) to run a small 15-item eval with secrets; never on every push (it would burn free quota).

B. User study mode (Objective 5: adaptive vs non-adaptive)
6. When STUDY_MODE is on: new students are assigned study_group by study_settings.assignment (random with balancing, or alternate); show a consent screen explaining the study (what's collected, anonymised, can withdraw); then pretest (form A, no AI, timed 20 min) → learning period (they use Cognexa; recommendations follow their group) → posttest (form B), unlocked by admin date or after N days.
7. Admin study page: enrolment counts per group, completion funnel, toggle study on/off, set the posttest unlock date, export an anonymised CSV (participant hash, group, pretest, posttest, normalized gain g = (post − pre)/(max − pre), quizzes taken, tutor questions, recommendations shown/clicked/completed, active days).
8. evaluation/study_analysis.ipynb: loads the CSV, describes both groups, tests the difference in normalized gain (Welch t-test and Mann-Whitney U), effect size (Cohen's d), plots, and a paragraph template for the report's results chapter. Include a power-analysis cell that states how many participants are needed to detect a medium effect, so the team can plan recruitment honestly.

Tests: metric functions (prerequisite hit rate, gain formula) unit-tested with hand-computed fixtures; group assignment balancing; CSV anonymisation (no emails/names).

Verify: run the full eval on dev (it may take a while within free limits; run it in batches if needed), commit the report, and paste the headline table into progressfile.md → Evaluation Results.

Finish with the Standard Wrap-up.
```

---

## Phase 13 — Hardening: security, performance, accessibility, observability, e2e

```text
Read CLAUDE.md and progressfile.md. Phase 13: production hardening. Plan first, then work through this checklist and record each item's result in progressfile.md.

Security
- Run a security review of the whole codebase: authz on every endpoint (write a test that enumerates all routes and asserts each is either explicitly public or requires auth), IDOR checks (user A can't access B's threads/notes/quizzes/feedback), RLS policies reviewed and tested, SQL/Cypher fully parameterised, file-upload limits and type checks, CORS limited to known origins, security headers on the web app (CSP that still allows what we use, HSTS, X-Frame-Options, Referrer-Policy), no secrets in the client bundle (grep the build output), dependency audit (npm audit, pip-audit) with fixes, rate limits on expensive non-AI endpoints too.
- Prompt-injection test suite: 15 adversarial prompts (ignore instructions, reveal system prompt, role-play jailbreaks, injected text in uploaded PDFs) → assert safe behaviour with FakeProvider for structure and a manual run on real models; document the results.

Performance
- Backend: connection pooling sized for Render free (512 MB RAM, 1 worker), Neo4j driver singleton, N+1 query check, indexes verified with EXPLAIN on the dashboard/history queries, gzip, pagination everywhere. Target p95 < 300 ms for non-AI endpoints on dev.
- Frontend: route-level code splitting (Cytoscape/Recharts/KaTeX loaded lazily), image optimisation, no layout shift, TanStack Query caching. Lighthouse ≥ 90 on landing, dashboard and tutor.
- Cold start UX on Render free verified (banner + warm-up).

Reliability & observability
- Graceful handling when Neo4j is paused/unreachable (clear error + the tutor degrades to plain RAG with a visible notice, logged), when Supabase is slow, and when both LLM providers fail.
- Structured logs with request_id across web → API; error boundary pages in Next.js; optional Sentry integration (free developer plan) behind an env var, off by default; /health/deep used by the keep-alive.
- Database backups: a script that exports Postgres app tables (pg_dump) and Neo4j (via export to concepts.yaml + chunks JSON) for manual backups, since free tiers have no backups. Document it.

Accessibility & UX polish
- axe checks in Playwright on every main page (0 serious/critical violations), keyboard-only walkthrough, focus rings visible in all themes, colour contrast verified for all 3 themes, reduced-motion respected, responsive at 360/768/1280/1920 px.
- Consistent loading/empty/error states everywhere; 404 and 500 pages designed.

E2E suite (Playwright, FakeProvider backend): sign up → onboarding diagnostic → dashboard → tutor question with trace → report answer → concept quiz → recommendation updates → notes → revision sheet → settings theme switch → sign out. Admin: approve a proposal, resolve a report, change a quota. Run in CI against docker services.

Finish with the Standard Wrap-up.
```

---

## Phase 14 — Bug hunt and fresh-eyes review

```text
Read CLAUDE.md and progressfile.md. Phase 14: find and fix bugs before deployment. Do not add features.

1. Fresh-eyes review: if subagents are available, spawn a reviewer subagent that has NOT seen the implementation history. Give it the report objectives (CLAUDE.md §1, progressfile.md Traceability Matrix) and ask it to review the codebase for correctness bugs, race conditions, security holes, unhandled errors, dead code, inconsistent API contracts between web and api, and any report objective that isn't actually implemented. If subagents aren't available, do this review yourself, file by file, starting with app/tutor, app/recommender, app/quiz, app/usage, the auth middleware and the SSE client.
2. Contract check: generate the OpenAPI schema from FastAPI and typed client types for the web app (openapi-typescript); fix every mismatch it reveals; add a CI step that fails if the generated types are stale.
3. Exploratory testing: run the app locally with real providers on dev and try to break it: empty inputs, very long inputs, unicode/emoji, rapid double-clicks, two tabs at once, expired session mid-stream, quota hit mid-stream, Neo4j stopped, network offline, back/forward navigation, mobile viewport.
4. For EVERY bug found: write a failing test first, fix it, confirm the test passes, and log it in progressfile.md Bug Log (ID, severity, area, symptom, root cause, fix, test, commit).
5. Re-run the entire verification suite (backend + frontend + e2e + validators). Zero failures and zero skipped tests without a written reason.
6. Update the Traceability Matrix: every report objective and every product feature must be "Done + Verified" with where it lives in the code, or listed under Known Limitations with a reason.

Finish with the Standard Wrap-up and a summary: bugs found/fixed by severity, and any remaining known issues.
```

---

## Phase 15 — Deployment (free tiers), keep-alive, production smoke test

```text
Read CLAUDE.md and progressfile.md. Phase 15: deploy Cognexa to production on free tiers. I (the human) will click through the dashboards; you prepare everything and give me exact step-by-step instructions where a dashboard action is needed. Never print secret values.

1. Backend container: apps/api/Dockerfile (python:3.12-slim, uv, non-root user, a single uvicorn worker bound to $PORT, healthcheck on /health, small image). Test the build and run it locally.
2. render.yaml blueprint: one free web service from the Dockerfile, health check path /health, env vars declared (sync: false for secrets), auto-deploy from main.
3. Vercel: apps/web as the project root; env vars (Supabase URL + anon/publishable key, NEXT_PUBLIC_API_URL); production and preview behaviour (previews point at the dev backend or are disabled; decide and document).
4. Production data: run the migrations on cognexa-prod (Supabase CLI `supabase db push` or the SQL editor; document exactly which); run seed_neo4j/seed_postgres/seed_vectors against prod using a local .env.production that is never committed; create the first admin user (script: promote by email).
5. Supabase prod auth config: site URL and redirect URLs for the Vercel domain, Google OAuth redirect (add the Vercel domain to the Google client's authorized origins), confirm that custom SMTP is configured (docs/PHASE0_SETUP.md Step 10; without it real users get no emails and templates can't be edited), then brand the email templates "Cognexa" (confirm, reset).
6. CORS ALLOWED_ORIGINS = the Vercel production domain (+ localhost for dev only).
7. .github/workflows/keepalive.yml: scheduled daily (and workflow_dispatch) GET of https://<render-url>/health/deep, which touches Postgres AND Neo4j so Aura Free (72 h idle pause) and Supabase Free (≈7 day idle pause) stay active; fail loudly if unhealthy. Note in docs that GitHub may disable scheduled workflows after 60 days of no repository activity, so someone must push or re-enable it.
8. docs/DEPLOYMENT.md: an exact, numbered, screenshot-free runbook (accounts → env vars table → deploy order → seed → first admin → verify → how to roll back → how to re-seed Neo4j if Aura deletes the instance → how to rotate keys → free-tier limits and what happens when they're hit).
9. Production smoke test script (scripts/prod_smoke.py + a manual checklist): health/deep green, sign up with a real email, Google login, ask the canonical recursion question and see call_stack in the trace, take a quiz, see the recommendation, open the knowledge map, report an answer, admin sees it, quota meter updates. Record the results in progressfile.md with the live URLs.

Finish with the Standard Wrap-up. Put the live URLs at the top of progressfile.md.
```

---

## Phase 16 — Documentation, diagrams, viva demo script

```text
Read CLAUDE.md and progressfile.md. Phase 16: documentation for the final report, viva and future maintainers. No feature changes.

1. README.md: polished overview with screenshots (from docs/screenshots), features, architecture diagram, stack, quick start, deployment link, evaluation headline results, team and guide, licence.
2. docs/ARCHITECTURE.md with Mermaid diagrams: system context, container diagram, the GraphRAG sequence diagram (Ask → Classify → Traverse → Gather → Answer + agentic step), recommender flowchart (R1–R5), the ER diagram for Postgres, the Neo4j schema, data seeding flow. Explain every design decision, linked to the Decisions Log.
3. docs/API.md generated from OpenAPI plus hand-written notes on SSE events and error codes.
4. docs/DEMO_SCRIPT.md: a 10-minute viva demo, minute by minute: landing page → sign in → ask the recursion overflow question (show the trace and the why-panel) → admin compare view (GraphRAG vs plain RAG side by side) → take a quiz and get it wrong → the recommender points to the prerequisite → the knowledge map → admin: PDF ingestion + proposal review → evaluation results page. Include a pre-demo checklist (warm up Render 2 minutes before, check /health/deep, switch to Titanium Light for the projector, have a backup screen recording in case the network fails) and likely examiner questions with crisp answers (why Neo4j, why rule-based, why not multi-agent, how you'd add a new subject, limitations, cost at scale).
5. docs/ADDING_A_SUBJECT.md: step-by-step guide to adding a new subject pack (concepts.yaml, content, questions, testset, validate, seed). Prove it works with a tiny 5-concept demo subject in data/subjects/_example/ that is seeded only in dev.
6. Final progressfile.md pass: complete, consistent, with a "Project Summary for the Final Report" section (what was built, results, limitations, future work: ML mastery predictor, multi-subject, diagram parsing, from report §1.7).

Finish with the Standard Wrap-up.
```

---

## Appendix A — Resume prompt (start of any new session)

```text
Read CLAUDE.md and progressfile.md fully. Tell me: (1) the current phase and its status, (2) what was last completed and verified, (3) any open bugs or failing checks, (4) the next concrete step. Then run the verification commands to confirm the repo is green before doing anything new. Don't start new work until I confirm.
```

## Appendix B — Bug fix prompt

```text
Read CLAUDE.md and progressfile.md. Bug report:
- What I did: <steps>
- What I expected: <expected>
- What happened: <actual, include error messages / screenshots / console output>
- Where: <page / endpoint / environment: local|prod>

Process: reproduce it first (tell me how you reproduced it), find the root cause (explain it), write a failing test, fix it, run the full verification suite, then log it in the progressfile.md Bug Log with symptom, root cause, fix, test and commit. Check whether the same bug pattern exists elsewhere and fix those too.
```

## Appendix C — DSA concept graph (source for `concepts.yaml`)

Edge convention: listed **prerequisites** must be learned before the concept. **Related** are associative links. Claude Code adds descriptions, aliases, keywords, difficulty and order_index. **Your team should review the edges.** This list is a strong starting draft, not gospel.

| Cluster | id | Name | Prerequisites | Related |
|---|---|---|---|---|
| foundations | discrete_math_basics | Discrete Math Basics (logs, sums, modular arithmetic) | — | — |
| foundations | variables_memory | Variables, Data Types & Memory | — | — |
| foundations | control_flow | Conditionals & Loops | variables_memory | — |
| foundations | functions | Functions & Parameters | control_flow | — |
| foundations | arrays | Arrays | control_flow | — |
| foundations | strings | Strings | arrays | — |
| foundations | pointers_references | Pointers & References | variables_memory | — |
| foundations | stack_heap_memory | Stack vs Heap Memory | pointers_references, functions | — |
| foundations | call_stack | Function Calls & the Call Stack | functions, stack_heap_memory | stack |
| foundations | bit_manipulation | Bit Manipulation | variables_memory | — |
| foundations | recursion | Recursion | call_stack | backtracking, divide_and_conquer |
| complexity | time_complexity | Time Complexity & Big-O | control_flow, discrete_math_basics | — |
| complexity | asymptotic_notation | Asymptotic Notation (O, Θ, Ω; best/avg/worst) | time_complexity | — |
| complexity | space_complexity | Space Complexity | time_complexity, stack_heap_memory | — |
| complexity | recurrence_relations | Recurrence Relations & Master Theorem | recursion, asymptotic_notation | — |
| complexity | amortized_analysis | Amortized Analysis | asymptotic_notation, dynamic_arrays | — |
| linear | dynamic_arrays | Dynamic Arrays | arrays, pointers_references, time_complexity | — |
| linear | singly_linked_list | Singly Linked List | pointers_references, stack_heap_memory | arrays |
| linear | doubly_circular_linked_list | Doubly & Circular Linked Lists | singly_linked_list | deque_circular_queue |
| linear | stack | Stack (ADT & implementations) | arrays, singly_linked_list | call_stack |
| linear | queue | Queue (ADT & implementations) | arrays, singly_linked_list | — |
| linear | deque_circular_queue | Deque & Circular Queue | queue | — |
| linear | priority_queue_adt | Priority Queue (ADT) | queue | binary_heap |
| linear | expression_evaluation | Expression Evaluation (infix/postfix) | stack | — |
| linear | monotonic_stack | Monotonic Stack | stack | sliding_window |
| searching_hashing | linear_search | Linear Search | arrays | — |
| searching_hashing | binary_search | Binary Search | arrays, time_complexity | bst |
| searching_hashing | two_pointers | Two Pointers | arrays | quick_sort |
| searching_hashing | sliding_window | Sliding Window | two_pointers | — |
| searching_hashing | prefix_sums | Prefix Sums | arrays | — |
| searching_hashing | hash_functions | Hash Functions | arrays, discrete_math_basics | — |
| searching_hashing | hash_tables | Hash Tables (chaining, open addressing) | hash_functions, singly_linked_list | — |
| searching_hashing | hash_sets_maps | Hash Sets & Maps in Practice | hash_tables | bst |
| sorting | elementary_sorts | Elementary Sorts (bubble, selection, insertion; stability) | arrays, time_complexity | — |
| sorting | divide_and_conquer | Divide & Conquer | recursion, recurrence_relations | — |
| sorting | merge_sort | Merge Sort | divide_and_conquer, elementary_sorts | — |
| sorting | quick_sort | Quick Sort | divide_and_conquer, elementary_sorts | — |
| sorting | heap_sort | Heap Sort | binary_heap, elementary_sorts | — |
| sorting | non_comparison_sorts | Counting, Radix & Bucket Sort | elementary_sorts | — |
| sorting | sorting_lower_bound | Comparison Sorting Lower Bound | elementary_sorts, asymptotic_notation, tree_basics | — |
| trees | tree_basics | Tree Terminology & Properties | singly_linked_list | — |
| trees | binary_tree | Binary Trees | tree_basics | — |
| trees | dfs_tree_traversals | Tree Traversals (pre/in/post-order) | binary_tree, recursion | dfs |
| trees | level_order_traversal | Level-Order Traversal | binary_tree, queue | bfs |
| trees | bst | Binary Search Trees | binary_tree, binary_search | — |
| trees | binary_heap | Binary Heap | binary_tree, priority_queue_adt | — |
| trees | avl_tree | AVL Trees | bst | — |
| trees | red_black_tree | Red-Black Trees | avl_tree | — |
| trees | b_tree | B-Trees | bst | — |
| trees | trie | Trie | tree_basics, strings | string_matching |
| trees | segment_tree | Segment Tree | dfs_tree_traversals, prefix_sums, divide_and_conquer | fenwick_tree |
| trees | fenwick_tree | Fenwick Tree (BIT) | prefix_sums, bit_manipulation | — |
| trees | disjoint_set_union | Disjoint Set Union (Union-Find) | tree_basics, amortized_analysis | — |
| graphs | graph_representation | Graph Basics & Representations | arrays, singly_linked_list | — |
| graphs | bfs | Breadth-First Search | graph_representation, queue | level_order_traversal |
| graphs | dfs | Depth-First Search | graph_representation, recursion, stack | dfs_tree_traversals, backtracking |
| graphs | topological_sort | Topological Sort | dfs | dp_fundamentals |
| graphs | cycle_detection | Cycle Detection | dfs | disjoint_set_union |
| graphs | connectivity_scc | Connected & Strongly Connected Components | dfs | — |
| graphs | dijkstra | Dijkstra's Shortest Path | bfs, binary_heap, greedy | bellman_ford |
| graphs | bellman_ford | Bellman-Ford | graph_representation, dijkstra | floyd_warshall |
| graphs | floyd_warshall | Floyd-Warshall | graph_representation, dp_fundamentals | — |
| graphs | minimum_spanning_tree | Minimum Spanning Tree (Kruskal & Prim) | graph_representation, disjoint_set_union, binary_heap, greedy | — |
| paradigms | backtracking | Backtracking | recursion | — |
| paradigms | greedy | Greedy Algorithms | elementary_sorts | — |
| paradigms | dp_fundamentals | Dynamic Programming (memoization & tabulation) | recursion, dynamic_arrays | divide_and_conquer |
| paradigms | dp_classic | Classic DP (knapsack, LCS, LIS, edit distance) | dp_fundamentals | — |
| paradigms | string_matching | String Matching (KMP, Rabin-Karp) | strings, hash_functions | — |
| paradigms | complexity_classes | P, NP & NP-Completeness | asymptotic_notation, backtracking | — |

**Roots:** discrete_math_basics, variables_memory. **Canonical demo chain:** functions → call_stack → recursion → dfs_tree_traversals. The order_index must respect all prerequisite edges. `validate_graph.py` enforces this.

## Appendix D — Git workflow & commit plan

**Workflow (single developer, `main` only; DEC-013, supersedes DEC-012)**

There is one branch, `main`. Never create branches, pull requests or worktrees.

1. Make the small commits listed below, one per logical step. **Before each commit run the full verification for the app you touched** (backend: `ruff check`, `ruff format --check`, `mypy`, `pytest`; frontend: `lint`, `typecheck`, `test`, `build`). Never commit a failing state.
2. At the end of each phase you push: `git push`. Watch the CI run on GitHub.
3. **If CI is red, fixing it is the top priority before any new work.** Reproduce it from a clean checkout (no `.next`, `node_modules`, `.venv` or `.env`), fix it, log it in the Bug Log, and push the fix.
4. When CI is green, tag the phase: `git tag -a v0.NN -m "Phase NN: <name>" && git push --tags`.
5. Last commit of every phase: `docs(progress): phase NN complete` (progressfile.md update).
6. Claude Code never pushes or tags; it prints the commands instead.

Note: run `git pull` first only if you ever commit from another machine or the GitHub web UI.

**Message format:** Conventional Commits, `type(scope): summary`. Types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `perf`, `ci`, `build`, `style`, `content`. Never commit `.env` files or keys.

| Phase | Commits (in order) | Tag |
|---|---|---|
| 0 | `chore: initial commit with CLAUDE.md, progressfile.md and build prompts` | v0.0 |
| 1 | `chore: scaffold monorepo layout and gitignore` · `feat(api): fastapi app factory, config, health endpoints` · `feat(web): next.js app with tailwind and shadcn/ui` · `feat(web): three-theme design system and /design showcase` · `build: docker compose for neo4j and pgvector` · `ci: lint, typecheck, test and build workflow` · `docs(progress): phase 01 complete` | v0.1 |
| 2 | `content(graph): dsa concepts.yaml with 69 concepts and edges` · `feat(scripts): graph validator with cycle detection` · `feat(graph): neo4j schema, constraints and GraphRepository` · `feat(db): supabase migrations, RLS policies and profile trigger` · `feat(scripts): idempotent neo4j and postgres seeders` · `test(graph): repository and validator integration tests` · `docs(progress): phase 02 complete` | v0.2 |
| 3 | `content(foundations): concept notes and questions` · `content(complexity): …` · `content(linear): …` · `content(searching): …` · `content(sorting): …` · `content(trees): …` · `content(graphs): …` · `content(paradigms): …` · `content(eval): 80-item evaluation test set and study sets` · `feat(scripts): content validator and snippet runner` · `feat(scripts): chunk seeding and vector embedding script` · `docs(progress): phase 03 complete` | v0.3 |
| 4 | `feat(api): supabase JWT verification and role guards` · `feat(api): profile, settings and admin user endpoints` · `feat(web): sign up, sign in, google oauth and password reset` · `feat(web): app shell, sidebar, usage meter and theme sync` · `feat(web): landing, how-it-works, about, privacy and terms pages` · `feat(web): settings, data export and account deletion` · `test(e2e): auth and route protection` · `docs(progress): phase 04 complete` | v0.4 |
| 5 | `feat(llm): provider interface with groq and gemini` · `feat(llm): router with retries, fallback and circuit breaker` · `feat(usage): quotas, rate limits, global cap and cost metering` · `feat(cache): response, classification and embedding cache` · `feat(guardrails): input limits and injection-safe prompts` · `feat(api): admin usage and settings endpoints` · `test(llm): fallback, quota and cache tests` · `docs(progress): phase 05 complete` | v0.5 |
| 6 | `feat(tutor): zero-shot classifier with hybrid fallback` · `feat(tutor): personalised cypher traversal` · `feat(tutor): token-budgeted context builder` · `feat(tutor): grounded streaming answer with citations` · `feat(tutor): bounded agentic controller` · `feat(tutor): plain RAG baseline and compare endpoint` · `feat(api): thread and message endpoints with SSE` · `test(tutor): canonical recursion→call_stack case and pipeline tests` · `docs(progress): phase 06 complete` | v0.6 |
| 7 | `feat(web): thread list with search, rename, archive and delete` · `feat(web): streaming chat with markdown, code and math` · `feat(web): live trace strip and why-this-answer panel` · `feat(web): diagnostic quick-check card` · `feat(web): feedback and report-answer dialog` · `feat(web): admin GraphRAG vs plain RAG compare view` · `test(e2e): tutor flow` · `docs(progress): phase 07 complete` | v0.7 |
| 8 | `feat(quiz): quiz sessions and six quiz modes` · `feat(quiz): auto-grading for all question types` · `feat(quiz): LLM short-answer grader with pending retry` · `feat(mastery): mastery update with decay and prerequisite signal` · `feat(web): quiz hub, player and results` · `feat(web): concept library and concept pages` · `feat(web): real onboarding diagnostic` · `test(quiz): grading and mastery tests` · `docs(progress): phase 08 complete` | v0.8 |
| 9 | `feat(recommender): rule engine R1–R5` · `feat(recommender): non-adaptive baseline and group routing` · `feat(review): SM-2-lite spaced review` · `feat(api): recommendations and review endpoints with logging` · `feat(web): next-best-step card and review page` · `test(recommender): table-driven rule tests` · `docs(progress): phase 09 complete` | v0.9 |
| 10 | `feat(api): dashboard aggregation and mastery graph endpoints` · `feat(web): progress dashboard with charts` · `feat(web): knowledge map with mastery colouring and PNG export` · `feat(notes): notes and bookmarks` · `feat(notes): grounded revision sheets with markdown/pdf export` · `test: dashboard, notes ownership and revision sheets` · `docs(progress): phase 10 complete` | v0.10 |
| 11 | `feat(admin): overview page` · `feat(admin): graph editor with cycle rejection and yaml export` · `feat(admin): LLM edge suggestions and pdf ingestion` · `feat(admin): proposal review queue` · `feat(admin): content and question bank editor` · `feat(admin): moderation queue, users, usage and settings` · `test(admin): role enforcement and proposal transactions` · `docs(progress): phase 11 complete` | v0.11 |
| 12 | `feat(eval): ragas harness with checkpointing` · `feat(eval): prerequisite hit rate and statistical tests` · `feat(admin): evaluation results page` · `feat(study): consent, group assignment, pre/post tests` · `feat(study): anonymised export and analysis notebook` · `ci: manual small-eval workflow` · `docs(eval): first full evaluation report` · `docs(progress): phase 12 complete` | v0.12 |
| 13 | `fix(security): …` (one per issue) · `test(security): route authz enumeration and IDOR tests` · `perf: lazy-load heavy client libraries` · `perf(api): indexes and pooling tuned` · `feat: graceful degradation when neo4j or LLMs are down` · `fix(a11y): …` · `feat(scripts): manual backup scripts` · `test(e2e): full student and admin journeys` · `docs(progress): phase 13 complete` | v0.13 |
| 14 | `fix(<area>): <bug summary> (BUG-NNN)`, one commit per bug, each with its regression test · `ci: fail on stale API types` · `docs(progress): phase 14 bug hunt results` | v0.14 |
| 15 | `build(api): production dockerfile` · `build: render blueprint` · `chore(web): vercel configuration` · `ci: daily keep-alive workflow` · `feat(scripts): promote-admin and prod smoke test` · `docs: deployment runbook` · `docs(progress): live URLs and smoke test results` | **v1.0.0** |
| 16 | `docs: README with screenshots` · `docs: architecture diagrams` · `docs: API reference` · `docs: viva demo script` · `feat(data): example subject pack and adding-a-subject guide` · `docs(progress): final project summary` | v1.0.1 |

**Rules of thumb**
- Commit whenever one logical step works and its tests pass (see step 1 above). Never commit a broken build to `main`.
- Bug fixes always reference the Bug Log ID: `fix(quiz): multi-select partial credit went negative (BUG-007)`.
- If Claude Code bundles many changes into one commit, ask it to split them with `git reset --soft` before you push (only for commits that are not pushed yet).

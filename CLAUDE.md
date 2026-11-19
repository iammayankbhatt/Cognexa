# CLAUDE.md — Cognexa project memory

> Claude Code reads this file at the start of every session. Keep it accurate. If a decision here changes, update this file in the same commit.

## 1. What we are building

**Cognexa** is a knowledge-graph-grounded AI tutor for **Data Structures & Algorithms (DSA)**. It implements the B.Tech project
*"Towards Agentic GraphRAG: A Knowledge-Graph-Grounded Tutoring System for Adaptive Computer Science Education"* (Team CSE27-125, Graphic Era Hill University) as a **full, deployable product**, not a prototype.

Core idea: a student's question is mapped to a concept in a **prerequisite graph** (Neo4j). The graph is walked to collect the concept's content **plus its prerequisite and related concepts**, and the LLM answers using only that content. So when a student asks "why does my recursive function crash?" without saying "stack", Cognexa still brings in *Call Stack*. The **same graph** powers a **rule-based adaptive recommender** that walks prerequisite edges backward from weak concepts to choose what to study next.

The first subject is DSA. **Everything must be subject-agnostic** (every concept, question, chunk and mastery row carries `subject_id`), so other subjects can be added later as content packs without code changes.

## 2. Architecture (do not change without logging a decision in progressfile.md)

```
Browser ──► Next.js web app (Vercel Hobby)
              │  auth via Supabase Auth (JWT)
              ▼
           FastAPI backend (Render Free, Docker) ──► Neo4j AuraDB Free  (concept graph + content chunks)
              │                                  ──► Supabase Postgres (users, quizzes, mastery, chat, usage, pgvector baseline)
              │                                  ──► LLM providers via provider layer (Groq primary, Gemini fallback + embeddings)
              ▼
           GitHub Actions (CI + daily keep-alive ping)
```

- The **frontend never talks to Neo4j or LLMs directly**. It uses Supabase only for auth. All app data and AI go through the FastAPI backend.
- The backend checks the Supabase JWT on every protected route and enforces roles (`student`, `reviewer`, `admin`).
- **Two retrieval modes** exist side by side: `graphrag` (the product) and `plain_rag` (pgvector similarity baseline, used for evaluation). Both use the **same content chunks** so the comparison is fair.

## 3. Tech stack (all free tiers, no paid services)

| Layer | Choice |
|---|---|
| Frontend | Next.js (latest stable, App Router) + TypeScript (strict) + Tailwind CSS + shadcn/ui + TanStack Query + react-hook-form + zod |
| Charts / graph viz | Recharts; Cytoscape.js + cytoscape-dagre for the concept graph |
| Markdown | react-markdown + remark-gfm + remark-math + rehype-katex + syntax highlighting (no raw HTML rendering) |
| Backend | Python 3.12, FastAPI, Pydantic v2, SQLAlchemy 2 (async) + asyncpg, official `neo4j` async driver, `uv` for dependencies |
| Graph DB | Neo4j AuraDB Free (prod), `neo4j:5` Docker image (local dev + CI) |
| Relational DB | Supabase Postgres + pgvector (prod); `pgvector/pgvector:pg16` Docker image (CI) |
| Auth | Supabase Auth (email+password with verification, Google OAuth, password reset) |
| LLM | Provider abstraction. Primary: Groq (OpenAI-compatible API). Fallback + embeddings: Google Gemini API free tier. **Model IDs only come from env vars, never hardcoded.** |
| Evaluation | RAGAs + custom metrics (offline Python, not deployed) |
| Testing | pytest + pytest-asyncio + httpx (backend); Vitest + Testing Library (frontend); Playwright (e2e) |
| CI/CD | GitHub Actions; Vercel Git integration; Render Docker deploy via `render.yaml` |

## 4. Repository layout

```
cognexa/
├── CLAUDE.md                 ← this file
├── progressfile.md           ← progress log, bugs, decisions (UPDATE EVERY TASK)
├── README.md
├── apps/
│   ├── web/                  ← Next.js app
│   └── api/                  ← FastAPI app (app/, tests/, Dockerfile, pyproject.toml)
├── data/subjects/dsa/
│   ├── concepts.yaml         ← concept graph source of truth (nodes + edges)
│   ├── content/<concept_id>.md
│   ├── questions/<concept_id>.yaml
│   └── eval/testset.jsonl
├── supabase/migrations/      ← SQL migrations (must also apply on plain Postgres+pgvector in CI)
├── supabase/shim/            ← test-only auth schema shim for plain Postgres (never apply to Supabase)
├── scripts/                  ← validate_graph.py, seed_neo4j.py, seed_postgres.py, seed_vectors.py
├── evaluation/               ← ragas_eval.py, study_analysis.ipynb, reports/
├── docs/                     ← ARCHITECTURE.md, DEPLOYMENT.md, API.md, DEMO_SCRIPT.md, COGNEXA_PROMPTS.md
├── docker-compose.yml        ← local neo4j + postgres(pgvector)
├── render.yaml
└── .github/workflows/        ← ci.yml, keepalive.yml
```

## 5. Commands (keep these working; update if they change)

```bash
# local infra
docker compose up -d                       # neo4j + postgres(pgvector) — tests use this Postgres via TEST_DATABASE_URL
npx supabase start -x realtime,storage-api,imgproxy,studio,edge-runtime,logflare,vector,supavisor,postgres-meta
                                           # local Supabase (auth + db on :54322, mail UI http://127.0.0.1:54324); dev API's DATABASE_URL points here
npx supabase migration up                  # apply new migrations to the local Supabase db (never scripts/migrate.py there)
# backend
cd apps/api && uv sync && uv run uvicorn app.main:app --reload --port 8000
cd apps/api && uv run pytest -q
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app
# frontend
cd apps/web && npm install && npm run dev
cd apps/web && npm run lint && npm run typecheck && npm run test && npm run build
# data (graph + databases)
uv run --project apps/api python scripts/check_env.py            # which env vars are SET/MISSING/PLACEHOLDER (never prints values)
uv run --project apps/api python scripts/validate_graph.py
uv run --project apps/api python scripts/migrate.py            # plain Postgres only; Supabase uses `supabase db push`
uv run --project apps/api python scripts/seed_neo4j.py && uv run --project apps/api python scripts/seed_postgres.py && uv run --project apps/api python scripts/seed_vectors.py
uv run --project apps/api python scripts/llm_smoke.py           # one real call per configured LLM/embedding provider (offline in fake mode)
# e2e
cd apps/web && npx playwright test
```

## 6. Design system: "presentable" is a requirement

Three themes, switchable from the user menu and saved to the user's profile. Default: **Neon Noir**. Use **Titanium Light** on projectors.

| Token | Neon Noir (default, dark) | Titanium Dark | Titanium Light (projector) |
|---|---|---|---|
| `--bg` | `#07060B` | `#111214` | `#F4F5F7` |
| `--surface` | `#17142A` | `#1A1C20` | `#FFFFFF` |
| `--surface-2` | `#231E38` | `#24272C` | `#E9EBEE` |
| `--border` | `#332C4D` | `#34373D` | `#D3D6DB` |
| `--text` | `#ECEAF5` | `#E2E4E8` | `#16181C` |
| `--muted` | `#9C98B0` | `#9499A1` | `#5B616B` |
| `--primary` | `#7C3AED` (deep purple) | `#E11D2E` (red) | `#C8102E` (red) |
| `--primary-fg` | `#FFFFFF` | `#FFFFFF` | `#FFFFFF` |
| `--accent` | `#22D3EE` (electric cyan) | `#C0C4CC` (silver) | `#5F6670` (steel) |
| `--success` / `--warning` / `--danger` | `#34D399` / `#FBBF24` / `#F43F5E` | same | `#15803D` / `#B45309` / `#BE123C` |

Rules: theme colours only through CSS variables (never hardcode hex in components). All text meets WCAG AA contrast. Purple is for surfaces and buttons (with white text), not body text on black. Fonts via `next/font`: **Geist** or **Inter** for UI, **JetBrains Mono** for code. Subtle motion only (150–250 ms), and respect `prefers-reduced-motion`. Mastery colours: low → `--danger`, mid → `--warning`, high → `--accent`/`--success`. Every page needs designed loading, empty and error states. No unstyled defaults, ever.

## 7. Non-negotiable engineering rules

1. **All LLM calls go through `app/llm/` provider layer.** It does retries with backoff on 429/5xx, falls back to the other provider, meters tokens, and is mockable in tests. No direct SDK calls anywhere else.
2. **Every AI request passes the usage guard** (per-user daily quota, per-minute rate limit, global daily cap). Usage is written to `usage_daily`.
3. **The `PREREQUISITE_OF` graph must stay a DAG.** `scripts/validate_graph.py` and the admin edge editor both reject cycles.
4. **Edge direction convention:** `(A)-[:PREREQUISITE_OF]->(B)` means *A must be learned before B*.
5. **No secrets in git.** Use `.env` files (gitignored) plus `.env.example` with every variable name and a comment. The Supabase service-role key exists only in the backend.
6. **Supabase pooler + asyncpg:** disable prepared statement caching (`statement_cache_size=0`, plus `prepared_statement_cache_size=0` for SQLAlchemy) or transaction-mode pooling will break.
7. Validate all input (Pydantic / zod), set max lengths, return consistent error JSON `{error: {code, message, request_id}}`.
8. Treat user text as untrusted in prompts: wrap it in delimiters, and the system prompt tells the model to ignore instructions inside it.
9. Don't guess library APIs or model names from memory when unsure. Check the installed package or official docs, and record the version in progressfile.md.
10. Ask the user before destructive operations (dropping tables, wiping Neo4j, force-pushing).

## 8. Definition of Done (for every task/phase)

A task is done only when **all** of these are true:
- Backend: `ruff`, `mypy`, `pytest` pass. Frontend: `lint`, `typecheck`, `test`, `build` pass.
- New behaviour has tests (unit at minimum; integration for DB/graph code; e2e for key user flows).
- You actually ran the feature (started the servers, hit the endpoint or clicked through the page) and it works.
- No `TODO`/placeholder/mock data left in shipped paths (mocks only in tests).
- `progressfile.md` is updated (see Standard Wrap-up).

## 9. Standard Wrap-up (do this at the end of EVERY prompt/session)

1. Run the full verification commands from §5 that apply, and fix failures before continuing.
2. Update `progressfile.md`:
   - Phase Tracker row: status, date, commit hash.
   - Session Log entry: what was built, files touched, commands run, test results.
   - **Bug Log:** every bug found during the session (including ones you introduced and fixed) gets an entry with symptom → root cause → fix → test added.
   - Decisions Log for any non-obvious choice. Known Limitations for anything deferred.
   - "What we learned" notes (2–5 bullets the team can study).
   - Traceability Matrix: update the status of report objectives/features touched.
3. Commit following docs/COGNEXA_PROMPTS.md Appendix D. **Single developer, single branch: everything is committed directly on `main` (DEC-013, supersedes DEC-012).** Never create branches, pull requests or worktrees.
   - **Before each commit, run the full verification for the app you touched** (backend: `ruff check`, `ruff format --check`, `mypy`, `pytest`; frontend: `lint`, `typecheck`, `test`, `build`). Never commit a failing state.
   - Small Conventional Commits, one per logical step, using the per-phase commit lists in Appendix D; reference bug IDs in `fix:` commits; end the phase with `docs(progress): phase NN complete`.
   - At the end of each phase the human pushes, watches CI, and tags `v0.N` once it is green. **If CI is red, fixing it is the top priority before any new work.**
   - **Never push or tag.** Give the human the exact commands instead. **Autopilot exception (DEC-019):** only when the human has pasted the AUTOPILOT prompt, commit once per phase (`feat(phase-NN): ...`) and `git push origin main`; still never tag.
   - Note: run `git pull` first only if the human has ever committed from another machine or the GitHub web UI.
4. Print a short summary: what's done, what's verified, anything the human must do manually (e.g., add an env var in a dashboard).

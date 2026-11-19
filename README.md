# Cognexa

**A knowledge-graph-grounded AI tutor for Data Structures & Algorithms.**

Cognexa maps a student's question to a concept in a **prerequisite graph** (Neo4j), walks the graph to collect that concept's content *plus its prerequisites and related concepts*, and has an LLM answer using only that content. So when a student asks "why does my recursive function crash?" without mentioning the stack, Cognexa still brings in *Call Stack*. The same graph powers a rule-based adaptive recommender that walks prerequisite edges backward from weak concepts to decide what to study next.

It is the full product implementation of the B.Tech project _"Towards Agentic GraphRAG: A Knowledge-Graph-Grounded Tutoring System for Adaptive Computer Science Education"_ (Team CSE27-125, Graphic Era Hill University). DSA is the first subject; everything carries a `subject_id` so other subjects can be added as content packs.

> **Status:** Phase 1 (scaffold, design system, CI) is complete. See [progressfile.md](progressfile.md) for the phase tracker, decisions and bug log.

## Architecture

```
Browser ──► Next.js web app (Vercel)
              │  auth via Supabase Auth (JWT)
              ▼
           FastAPI backend (Render, Docker) ──► Neo4j AuraDB   (concept graph + content chunks)
              │                              ──► Supabase Postgres (users, quizzes, mastery, chat, pgvector)
              │                              ──► LLM providers (Groq primary, Gemini fallback + embeddings)
              ▼
           GitHub Actions (CI + daily keep-alive)
```

The frontend never talks to Neo4j or an LLM directly. See [CLAUDE.md](CLAUDE.md) for the engineering rules.

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js (App Router) · TypeScript (strict) · Tailwind CSS 4 · shadcn/ui · TanStack Query |
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 (async) + asyncpg · neo4j driver · uv |
| Data | Neo4j 5 (graph) · Postgres 16 + pgvector (relational + vectors) |
| Auth / LLM | Supabase Auth · Groq (primary) · Google Gemini (fallback + embeddings) |
| Quality | ruff · mypy (strict) · pytest · Vitest · Playwright · GitHub Actions |

Exact installed versions are tracked in [progressfile.md](progressfile.md#3-tech-stack).

## Run locally

**Prerequisites:** Docker, Node.js 22+, Python 3.12 and [uv](https://docs.astral.sh/uv/).

```bash
# 1. Local infrastructure (Neo4j + Postgres/pgvector)
cp .env.example .env              # optional: defaults already work
docker compose up -d --wait

# 2. Backend  → http://localhost:8000  (docs at /docs)
cd apps/api
cp .env.example .env
uv sync
uv run uvicorn app.main:app --reload --port 8000

# 3. Frontend → http://localhost:3000
cd apps/web
cp .env.example .env.local
npm install
npm run dev
```

Check it works: `curl localhost:8000/health` returns `{"status":"ok"}`, and `curl localhost:8000/health/deep` reports Postgres and Neo4j status and latency. In development, open <http://localhost:3000/design> for the design-system reference (it returns 404 in production).

> **Port note:** local Postgres is published on host port **5433** (not 5432) so it doesn't collide with a native Postgres install.

## Checks

```bash
# backend
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
# frontend
cd apps/web && npm run lint && npm run typecheck && npm run test && npm run build
# end-to-end (starts the dev server itself)
cd apps/web && npm run e2e
# regenerate design screenshots into docs/screenshots/phase1/
cd apps/web && npm run screenshots
```

The backend's live-database tests run when `DATABASE_URL` and `NEO4J_*` are set (CI does this with service containers) and are skipped otherwise.

## Design system

Three themes, switchable from the theme switcher and stored in `localStorage` (profile sync arrives in Phase 4): **Neon Noir** (default), **Titanium Dark**, and **Titanium Light** (for projectors). Colours exist only as CSS variables on `[data-theme]` and are exposed to Tailwind (`bg-surface`, `text-muted`, `bg-primary`, …). A unit test checks WCAG AA contrast for every text/background pair in all three themes. Screenshots are in [docs/screenshots/phase1/](docs/screenshots/phase1/).

## Repository layout

```
apps/web/            Next.js app            apps/api/        FastAPI app
data/subjects/dsa/   concept graph, content, questions, eval set
supabase/migrations/ SQL migrations         scripts/         validators and seeders
evaluation/          RAGAs + analysis       docs/            architecture, deployment, prompts
```

## Documentation

- [CLAUDE.md](CLAUDE.md): project memory and engineering rules
- [progressfile.md](progressfile.md): progress log, decisions, bugs, traceability matrix
- [docs/COGNEXA_PROMPTS.md](docs/COGNEXA_PROMPTS.md): phase-by-phase build prompts

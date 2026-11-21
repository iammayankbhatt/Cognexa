# Cognexa

**A knowledge-graph-grounded AI tutor for Data Structures & Algorithms.**

A student asks *"why does my recursive function crash for big inputs?"* without ever saying "stack". Cognexa maps the question to a concept in a **prerequisite graph** (Neo4j), walks the graph to collect that concept's notes **plus its prerequisites**, and has an LLM answer using only that content. So the answer explains the **call stack** first, the real cause. The same graph powers a **rule-based adaptive recommender** that walks prerequisite edges backwards from a student's weak concepts to the first real gap.

Cognexa is the full product implementation of the B.Tech project *"Towards Agentic GraphRAG: A Knowledge-Graph-Grounded Tutoring System for Adaptive Computer Science Education"* (Team CSE27-125, Graphic Era Hill University). DSA is the first subject; every row carries a `subject_id`, so new subjects are content packs, not code changes.

| Tutor with "Why this answer?" | Progress dashboard | Knowledge map |
|---|---|---|
| ![Tutor answer with the Why panel](docs/screenshots/phase7/2-answer-why-panel-titanium-light.png) | ![Dashboard](docs/screenshots/phase10/dashboard-titanium-light.png) | ![Knowledge map](docs/screenshots/phase10/knowledge-map-titanium-light.png) |
| **GraphRAG vs plain RAG (admin)** | **Quiz feedback** | **Landing page** |
| ![Compare view](docs/screenshots/phase7/5-compare-titanium-light.png) | ![Quiz feedback](docs/screenshots/phase8/2-quiz-feedback-titanium-light.png) | ![Landing](docs/screenshots/phase4/landing-neon-noir.png) |

## Features

- **GraphRAG tutor:** LLM classifier with a hybrid fallback (Neo4j fulltext + embeddings, rank fusion) → prerequisite traversal personalised by mastery → token-budgeted context → streamed answer with concept citations and follow-ups. A **bounded agentic step** (at most two decisions) can ask a quick-check question before answering.
- **Explainability:** a live trace and a "Why this answer?" panel show the matched concepts, the exact graph edges that brought content in, the chunks used, and the model and tokens.
- **Plain-RAG baseline** over the same chunks, with a side-by-side compare view for reviewers and admins (and an optional student switch).
- **Quizzes:** six modes (concept, adaptive, diagnostic, review, pre/post-test) and five question types, auto-graded, with an LLM judge for short answers; misconception-aware feedback.
- **Mastery model** with prerequisite penalties and decay; **spaced review** (1 → 3 → 7 → 14 → 30 days).
- **Adaptive recommender** (rules R1-R5: root-cause repair, focused review, due review, forward progress, new learner) and a non-adaptive baseline for the study.
- **Progress dashboard, knowledge map** (Cytoscape DAG coloured by mastery), **notes** and AI **revision sheets**.
- **Admin console:** graph editor with cycle checks, LLM-proposed edges and document ingestion (PDF/Markdown) reviewed by a human, content and question editor, moderation queue, users, quotas and cost.
- **Evaluation:** RAGAs + custom metrics (prerequisite hit rate, concept accuracy, off-topic decline) on an 85-item test set, and a **user-study mode** (random assignment, matched pre/post-tests, anonymised export, analysis notebook).
- **Guardrails:** per-user daily quota, per-minute rate limit and global daily cap; response caching; prompt-injection defences with a 15-attack test suite; three accessible themes (Neon Noir, Titanium Dark, Titanium Light for projectors).

## Architecture

```mermaid
flowchart LR
  B["Browser<br/>Next.js on Vercel"] -->|"sign-in"| A[("Supabase Auth")]
  B -->|"JSON + SSE, Bearer JWT"| API["FastAPI on Render<br/>LLM provider layer + usage guard"]
  API --> N[("Neo4j AuraDB<br/>concept graph + chunks")]
  API --> P[("Supabase Postgres + pgvector<br/>users, quizzes, mastery, chat, usage")]
  API --> L["Groq (primary)<br/>Gemini (fallback + embeddings)"]
  GH["GitHub Actions<br/>CI + daily keep-alive"] --> API
```

The browser never talks to Neo4j or an LLM directly. Details, sequence diagrams, the data model and the design decisions: [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md).

## Tech stack

| Layer | Choice |
| --- | --- |
| Frontend | Next.js 16 (App Router) · TypeScript (strict) · Tailwind CSS 4 · shadcn/ui · TanStack Query · Recharts · Cytoscape.js |
| Backend | Python 3.12 · FastAPI · Pydantic v2 · SQLAlchemy 2 Core (async) + asyncpg · official neo4j driver · uv |
| Data | Neo4j 5 (AuraDB Free) · Postgres + pgvector (Supabase) |
| Auth / AI | Supabase Auth (email + Google) · Groq · Google Gemini (model ids from env vars) |
| Quality | ruff · mypy · pytest (512 tests) · Vitest (215) · Playwright (52 e2e, axe accessibility) · GitHub Actions |

## Quick start (local, no API keys needed)

**Prerequisites:** Docker, Node.js 22+, Python 3.12, [uv](https://docs.astral.sh/uv/).

All commands run from the repository root.

```bash
# 1. Neo4j (+ a plain Postgres used by the tests) and the local Supabase stack (auth, database, mail UI).
#    `supabase start` applies the SQL migrations and prints the local URL and keys.
docker compose up -d --wait
npx supabase start -x realtime,storage-api,imgproxy,studio,edge-runtime,logflare,vector,supavisor,postgres-meta
npx supabase status            # local API URL, anon key, service-role key

# 2. Environment files
cp apps/api/.env.example apps/api/.env
cp apps/web/.env.example apps/web/.env.local
```

Edit the two files for the local Supabase stack:

- `apps/api/.env`: `DATABASE_URL=postgresql+asyncpg://postgres:postgres@127.0.0.1:54322/postgres`, `SUPABASE_URL=http://127.0.0.1:54321`, `SUPABASE_SERVICE_ROLE_KEY=<service-role key from supabase status>`. `SUPABASE_JWKS_URL` can be left empty: it is derived from `SUPABASE_URL`.
- `apps/web/.env.local`: `NEXT_PUBLIC_SUPABASE_URL=http://127.0.0.1:54321`, `NEXT_PUBLIC_SUPABASE_ANON_KEY=<anon key>`, `NEXT_PUBLIC_API_URL=http://localhost:8000`.

```bash
# 3. Check the variables (names and SET / MISSING / PLACEHOLDER only, never values), seed, run the API
uv run --project apps/api python scripts/check_env.py
uv run --project apps/api python scripts/seed_neo4j.py
uv run --project apps/api python scripts/seed_postgres.py
uv run --project apps/api python scripts/seed_vectors.py
cd apps/api && uv sync && uv run uvicorn app.main:app --reload --port 8000     # http://localhost:8000/docs

# 4. Web app, in a second terminal (from the repository root)
cd apps/web && npm install && npm run dev                                    # http://localhost:3000
```

With `LLM_PRIMARY_PROVIDER=fake` and `EMBEDDING_PROVIDER=fake` (the defaults in `.env.example`) everything works offline: retrieval, traces, quizzes and recommendations are real, and answers are assembled from the retrieved notes. Add Groq and Gemini keys for real model answers ([docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) §2). Sign-up confirmation e-mails appear in the Supabase mail UI at <http://127.0.0.1:54324>. The docker Postgres on port **5433** is used by the test suite (`TEST_DATABASE_URL`).

## Checks

```bash
cd apps/api && uv run ruff check . && uv run ruff format --check . && uv run mypy app && uv run pytest -q
cd apps/web && npm run lint && npm run typecheck && npm run test && npm run build && npm run check:bundle
cd apps/web && npx playwright test                                   # e2e (needs the local stack + API)
uv run --project apps/api python scripts/validate_graph.py           # concept graph is a valid DAG
uv run --project apps/api python scripts/validate_content.py --strict
```

CI runs all of these plus a container build and the full Playwright suite against a throwaway Supabase stack.

## Deployment

Free tiers only: Vercel (web), Render (API, Docker), Supabase (auth + Postgres), Neo4j AuraDB Free, Groq and Gemini free tiers, GitHub Actions keep-alive. The step-by-step runbook (accounts, environment variables, deploy order, seeding, first admin, smoke test, rollback, key rotation, free-tier limits) is [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md).

**Live app:** not deployed yet. The URLs will be added here and in [progressfile.md](progressfile.md) §0 after the production smoke test.

## Evaluation

85 test questions in five categories, both retrieval modes over the same notes and model. The headline metric is the **prerequisite hit rate** on the 27 questions that describe a symptom without naming the prerequisite (did the retrieved context include the missing prerequisite?).

| Run | Plain RAG | GraphRAG | Significance |
|---|---|---|---|
| Offline run with deterministic fake models (`evaluation/reports/fake-offline-full/`) | 0.30 | **0.74** | Wilcoxon p = 0.0027, rank-biserial r = 0.75 |

The fake-model run measures retrieval only. Answer-quality metrics (RAGAs faithfulness, relevancy, context precision and recall) and the final numbers come from the real-model run (`evaluation/ragas_eval.py`), shown on `/admin/evaluation`. The user study design and analysis are in `evaluation/study_analysis.ipynb`.

## Documentation

| Document | For |
|---|---|
| [docs/ARCHITECTURE.md](docs/ARCHITECTURE.md) | system, containers, GraphRAG sequence, recommender, data model, design decisions |
| [docs/API.md](docs/API.md) | conventions, error codes, SSE events, generated endpoint reference |
| [docs/DEPLOYMENT.md](docs/DEPLOYMENT.md) | production runbook |
| [docs/ADDING_A_SUBJECT.md](docs/ADDING_A_SUBJECT.md) | adding a subject pack (worked example: `data/subjects/_example/`) |
| [docs/DEMO_SCRIPT.md](docs/DEMO_SCRIPT.md) | 10-minute viva demo and examiner Q&A |
| [progressfile.md](progressfile.md) | phase tracker, traceability matrix, decisions, bug log, limitations, final summary |
| [CLAUDE.md](CLAUDE.md) | engineering rules |

## Repository layout

```
apps/web/              Next.js app                 apps/api/           FastAPI app (app/, tests/, Dockerfile)
data/subjects/dsa/     concept graph, notes, questions, eval set     data/subjects/_example/  demo subject pack
supabase/migrations/   SQL migrations              scripts/            validators, seeders, smoke tests, backups
evaluation/            RAGAs harness + study analysis                docs/               the documents above
```

## Team

Ansh Karki (2318402) · Mayank Bhatt (2319093) · Divyanshi Kaushik (2318770) · Harshita Pant (2318850)
Guide: Mr. Akash Chauhan, Assistant Professor · Graphic Era Hill University, Dehradun · Team CSE27-125

## Licence

No licence has been chosen yet, so all rights are reserved by the authors. The team will add a `LICENSE` file before the code is shared more widely.

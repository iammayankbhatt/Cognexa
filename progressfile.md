# Cognexa — Progress File

> The single source of truth for **what has been built, how, with what, what broke, and how it was fixed**.
> Claude Code updates this at the end of every session (CLAUDE.md §9). The team reads it to study the project and to write the final report.
> Rule: **never delete history.** Mark things superseded instead.

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
| Repository | _TBD_ |
| Live web app | _TBD (Vercel)_ |
| Live API | _TBD (Render)_ |
| Current phase | Phase 0 — Manual setup |
| Overall status | 🔴 Not started |

Status legend: 🔴 Not started · 🟡 In progress · 🟢 Done + verified · ⚠️ Done with known issues · ⏸️ Blocked

---

## 1. One-paragraph summary (keep current)

Cognexa is a GraphRAG-based AI tutor for DSA. A student's question is classified to concepts in a Neo4j prerequisite graph. The graph is walked to collect the concept's content plus its (personally weak) prerequisites, and the LLM answers using only that content, citing concepts. The same graph powers a rule-based recommender that walks prerequisite edges backward from weak concepts to the real gap. Around this core is a full product: auth and roles, quiz engine with auto-grading, mastery tracking, progress dashboard, knowledge map, notes and revision sheets, chat history, feedback and reporting, admin console with LLM-proposed and human-approved graph edits, usage limits and cost metering, and an evaluation suite (RAGAs + a user-study mode). Everything runs on free tiers.

---

## 2. Report → Feature Traceability Matrix

Update the **Status** and **Where in code** columns as phases complete. Examiners will ask "where is objective X?". This table answers it.

| # | Report requirement (source) | Cognexa feature | Phase | Status | Where in code / evidence |
|---|---|---|---|---|---|
| O1 | KG of 40–80 core concepts in Neo4j with PREREQUISITE_OF and RELATED_TO (Obj. 1) | 69-concept DSA graph, validator, seed | 2 | 🔴 | |
| O2a | Question → concept mapping by LLM, zero-shot (Obj. 2, §1.8) | Classifier + hybrid fallback | 6 | 🔴 | |
| O2b | Graph traversal for prerequisite + related content (Obj. 2) | Cypher traversal, personalised ranking | 6 | 🔴 | |
| O2c | LLM generates grounded answer from retrieved context (Obj. 2) | Answer stage + citations + SSE | 6, 7 | 🔴 | |
| O3a | Rule-based recommender: weak concepts → prerequisite to review (Obj. 3) | Rules R1–R5 | 9 | 🔴 | |
| O3b | Uses quiz performance AND questions asked (Abstract) | Mastery + concept_interest signal | 8, 9 | 🔴 | |
| O4 | Functional end-to-end system (Obj. 4) | Full product, deployed | 1–15 | 🔴 | |
| O5a | User study: adaptive vs non-adaptive baseline (Obj. 5) | Study mode, groups, pre/post tests, export | 9, 12 | 🔴 | |
| O5b | Comparison against plain, non-graph RAG (§1.9) | plain_rag mode + compare view + eval | 6, 12 | 🔴 | |
| O5c | RAGAs reference-free metrics (§2.2 [10]) | ragas_eval.py + admin eval page | 12 | 🔴 | |
| G1 | LLM proposes tags, human verifies against fixed schema (Gap I, §3.4) | Proposals pipeline + review queue + PDF ingestion | 11 | 🔴 | |
| G2 | Prerequisites retrieved via explicit Cypher traversal (Gap II) | Traversal stage + "Why this answer?" panel | 6, 7 | 🔴 | |
| G3 | One graph powers both tutor and recommender (Gap III) | Shared GraphRepository | 6, 9 | 🔴 | |
| T | "Agentic" (title) | Bounded agentic controller (answer / diagnostic check / expand) | 6 | 🔴 | |
| X | Explainability: show the edge responsible for a retrieval (§2.3) | Trace + mini-graph in UI | 7 | 🔴 | |
| F | Future scope designed for: multi-subject, ML mastery, diagram parsing (§1.7) | subject_id everywhere, ADDING_A_SUBJECT.md | 2, 16 | 🔴 | |

### Product features (beyond the report)

| Feature | Phase | Status | Where in code |
|---|---|---|---|
| Email/password + Google login, verification, reset, roles (student/reviewer/admin) | 4 | 🔴 | |
| Three themes (Neon Noir, Titanium Dark, Titanium Light) | 1, 4 | 🔴 | |
| Landing, How-it-works, About, Privacy, Terms pages | 4 | 🔴 | |
| Onboarding + diagnostic quiz | 4, 8 | 🔴 | |
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
| Admin: graph editor, content/question editor, moderation, users, usage, settings | 11 | 🔴 | |
| Data export + account deletion | 4 | 🔴 | |
| Security hardening, a11y, performance, observability, backups | 13 | 🔴 | |
| Free-tier deployment + keep-alive | 15 | 🔴 | |

---

## 3. Tech Stack

> Claude Code fills **Version** with the exact installed version, and adds rows for any new dependency with a reason.

| Layer | Technology | Version | Why we chose it | Free-tier limit to watch |
|---|---|---|---|---|
| Frontend framework | Next.js (App Router) + TypeScript | | SSR, routing, Vercel-native | Vercel Hobby: personal / non-commercial use |
| Styling / UI | Tailwind CSS + shadcn/ui | | Fast, consistent, themeable via CSS variables | — |
| Data fetching / forms | TanStack Query, react-hook-form, zod | | Caching, validation | — |
| Charts / graph viz | Recharts, Cytoscape.js + dagre | | Themed charts; DAG layout for prerequisite graph | — |
| Backend | FastAPI + Pydantic v2 (Python 3.12, uv) | | Async, typed, Python AI ecosystem | Render Free: sleeps after 15 min, ~1 min cold start, 512 MB RAM |
| Graph database | Neo4j AuraDB Free (prod) / neo4j:5 Docker (dev, CI) | | Native graph + Cypher, explainable traversal | Pauses after 72 h idle; small node/relationship caps; no backups |
| Relational DB | Supabase Postgres + pgvector | | Auth + Postgres + vectors in one free service | 500 MB DB, pauses after ~7 days idle, 2 free projects |
| Auth | Supabase Auth | | Email, Google OAuth, JWT | 50k MAU |
| LLM (primary) | Groq (OpenAI-compatible) | model: _env_ | Fast, generous free tier, no training on data | Per-model RPM/RPD/TPM (see console) |
| LLM (fallback) + embeddings | Google Gemini API | model: _env_ | Free tier, embeddings | Low free RPD; prompts may be used to improve products |
| Evaluation | RAGAs, scipy, matplotlib | | Reference-free RAG metrics (report [10]) | Uses LLM quota, so run in batches |
| Testing | pytest, Vitest, Playwright, axe | | Unit / integration / e2e / a11y | — |
| CI/CD | GitHub Actions, Vercel, Render | | Free automation | Scheduled workflows disabled after 60 days of repo inactivity |

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
| 1 | Scaffold, design system, CI | 🔴 | | | | | |
| 2 | Databases + DSA concept graph | 🔴 | | | | | |
| 3 | Content, question bank, eval test set | 🔴 | | | | | |
| 4 | Auth, roles, app shell, public pages | 🔴 | | | | | |
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

_(no sessions yet)_

---

## 7. Bug Log

### 7.1 Bug index

Severity: **S1** critical (data loss, security, app down) · **S2** major (feature broken) · **S3** minor (workaround exists) · **S4** cosmetic.

| ID | Date found | Phase | Severity | Area | Short symptom | Status | Fixed in commit | Regression test |
|---|---|---|---|---|---|---|---|---|
| _BUG-001_ | | | | | | Open / Fixed / Won't fix | | |

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

_(no bugs yet)_

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

---

## 9. Known Limitations & Tech Debt

| ID | Description | Impact | Plan |
|---|---|---|---|
| LIM-001 | Free-tier cold starts (Render ~1 min) | First request slow | Warm-up on page load; keep-alive; paid instance if ever needed |
| LIM-002 | No managed backups on free tiers | Data-loss risk | Manual backup script (Phase 13); Neo4j re-seedable from YAML |
| LIM-003 | Per-minute rate limiter is in-memory | Only correct with one backend instance | Fine on Render free (1 instance); move to Redis if scaled |
| LIM-004 | LLM free-tier quotas | Global daily cap may be hit during heavy use | Quotas, caching, AI-free Review mode still works |

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
| `ALLOWED_ORIGINS` | api | CORS origins |
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

> Filled in during Phase 3. A team member ticks a concept only after checking its notes, code and questions.

| Cluster | Concept | Notes reviewed | Questions reviewed | Reviewer | Date |
|---|---|---|---|---|---|
| _foundations_ | _call_stack_ | ☐ | ☐ | | |

---

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

---

## 15. Project Summary for the Final Report

_(Written in Phase 16: what was built, key results, limitations, future work.)_

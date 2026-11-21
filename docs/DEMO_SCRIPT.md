# Viva demo script (10 minutes)

> For the team presenting Cognexa at the viva. The goal is one clear story: **a question that never names its real cause gets the right answer because the concept graph brings the cause in, and the same graph then tells the student what to study next.** Every step below has a fallback if something misbehaves.

## Before the demo (do this 15 minutes earlier)

**Accounts and data**
- [ ] A **student** demo account that has completed onboarding, with low mastery on Call Stack (take a Call Stack quiz and get most answers wrong the day before). This makes the quick check and the root-cause recommendation appear.
- [ ] An **admin** account (promoted with `scripts/promote_admin.py`), signed in on a second browser profile.
- [ ] A short text-based DSA PDF (5-10 pages) on the desktop for the ingestion step.
- [ ] One finished evaluation run visible on `/admin/evaluation` (the real-model run from `evaluation/ragas_eval.py --push`, Human Action 18; otherwise the committed fake-mode run).

**Warm-up**
- [ ] Open the Render API URL `/health/deep` **2 minutes before** (Render Free sleeps after 15 minutes idle; the first request takes about a minute). Status must be `ok` for Postgres and Neo4j.
- [ ] Open the Vercel site once and sign in on both profiles.
- [ ] Ask the tutor one throwaway question so the model connection is warm.

**Projector**
- [ ] Switch both accounts to **Titanium Light** (user menu → Theme). Dark themes wash out on projectors.
- [ ] Browser zoom 125 %, close other tabs, notifications off.

**Fallbacks**
- [ ] A **screen recording** of this whole script on the desktop (record it the day before). If the network or a free tier fails, play it and narrate.
- [ ] Screenshots in `docs/screenshots/` (phase 7 tutor, phase 10 dashboard and knowledge map) as a second fallback.
- [ ] Know the local fallback: `docker compose up -d`, the Supabase local stack, API and web on the laptop with fake providers (answers are assembled from the notes, retrieval and trace are real).

## Minute by minute

| Time | Screen | Do | Say (one or two sentences) |
|---|---|---|---|
| 0:00 | Landing page | Scroll once: the failure-case animation and the pipeline. | "Students often ask about a symptom, not the concept they are missing. Plain retrieval matches words; Cognexa matches the prerequisite graph." |
| 0:45 | Sign in (student) | Sign in; the dashboard shows mastery, the **Next best step** card and the AI usage meter. | "Everything is behind Supabase Auth; the backend checks the token and role on every request." |
| 1:30 | Tutor | Ask: *"Why does my recursive function crash for big inputs with maximum recursion depth exceeded?"* Point at the trace strip ("Looking at: Recursion, Call Stack ..."). | "The question never says 'stack'. The classifier maps it to Recursion, and the graph walk brings in Call Stack because it is a prerequisite." |
| 2:15 | Tutor | The **quick check** appears (Call Stack is weak for this student). Answer it briefly; the tutor continues. | "This is the bounded agentic step: at most two decisions per turn, here 'check the student first'." |
| 3:00 | Why this answer? | Open the panel: matched concepts, the mini graph with the `call_stack → recursion` edge, the chunks used, the model and tokens. | "Every answer is explainable: you can see which edge brought which content in." |
| 3:45 | Admin compare view | On the admin profile: Tutor → **Compare with plain RAG**, ask the same question. | "Same notes, same model, same budget. Plain RAG retrieves by similarity and misses the call stack; GraphRAG brings it in." |
| 4:45 | Quiz | Back on the student: Learn → Recursion → **Practice this concept**. Answer one question wrong on purpose and read the feedback (misconception, diagnosed prerequisite). | "Quizzes are auto-graded; wrong options carry the misconception they target, and the mastery model updates." |
| 5:45 | Results / dashboard | Show the **Next best step**: it points at the prerequisite (R1 root-cause repair) with its path. | "The recommender walks the same graph backwards from the weak concept to the first gap whose own prerequisites are known." |
| 6:30 | Knowledge map | `/app/graph`: colours by mastery, click a node, **Show my path**. | "One graph powers the tutor, the recommender and this map." |
| 7:15 | Admin: proposals | Admin → Proposals → upload the PDF. Open one proposal, show concept, kind and confidence; approve it. | "The LLM proposes, a human approves against a fixed schema. Nothing enters the graph without review." |
| 8:15 | Admin: evaluation | `/admin/evaluation`: GraphRAG vs plain RAG by category (prerequisite hit rate on unnamed-prerequisite questions), drill into one item side by side. | "Our evaluation uses 85 questions, 27 of them describe a symptom without naming the prerequisite. This is where the graph matters." |
| 9:00 | Admin: usage | `/admin/usage`: requests, tokens, estimated cost, cache hit rate. | "It runs entirely on free tiers, with per-user quotas, a global cap and caching." |
| 9:30 | Wrap-up | Back to the landing page. | "Knowledge-graph grounding for answers, the same graph for adaptivity, and human review for the graph itself. Thank you." |

If time runs short, drop the usage step and the knowledge map; never drop the tutor question, the Why panel or the compare view.

## If something goes wrong

| Problem | Do this |
|---|---|
| The API takes long on the first request | Say "the free tier is waking up" and continue on the landing page; the web shows a "waking up" banner. Warm it up earlier next time. |
| An answer is slow or the provider is rate-limited | The provider layer retries and falls back to the second provider automatically; keep talking about the trace, which arrives first. |
| The quick check does not appear | The student's Call Stack mastery is not low enough; continue, and show the Why panel's "weak prerequisite" marker instead. |
| Neo4j is paused or down | The tutor answers from plain RAG and shows a notice; say so, then switch to the screen recording for the graph parts. |
| No network | Play the screen recording. |

## Likely examiner questions

**Why Neo4j and not just Postgres?** Prerequisite walks are variable-length path queries (`(a)-[:PREREQUISITE_OF*1..2]->(b)`), which are natural and readable in Cypher and fast on a graph of 69 concepts. Postgres could do it with recursive CTEs, but the graph is the core idea, and we also show it to users and edit it in an admin editor with cycle checks. Postgres still holds everything per-user (quizzes, mastery, chat, usage) and the vector baseline.

**Why a rule-based recommender instead of machine learning?** It works from the first day with no training data, every recommendation can be explained ("Call Stack, because Recursion is weak and Call Stack is its unmastered prerequisite"), and it is fully testable with tables. An ML mastery predictor is listed as future work once study data exists.

**Why not a multi-agent system?** A bounded controller with at most two steps gives the useful agentic behaviour (check the student first, widen the search) without unbounded loops, latency or cost on free tiers, and it is testable. Multi-agent frameworks add calls and failure modes without a clear gain for one tutoring turn.

**How do you know GraphRAG is better?** Two ways. Offline: 85 test questions in five categories, both modes on the same chunks and model, with prerequisite hit rate, concept accuracy and RAGAs metrics (faithfulness, answer relevance, context precision), with significance tests. Online: a user study mode with random assignment to adaptive vs non-adaptive groups and matched pre/post-tests, reported as normalized gain.

**How would you add a new subject?** Write a content pack: `concepts.yaml`, one note per concept, questions, optionally a test set; validate and seed. No code changes, because every row carries `subject_id`. We proved it with a 5-concept Number Systems demo pack (docs/ADDING_A_SUBJECT.md). Prompt wording and a subject picker in the web app are the remaining DSA-specific parts.

**What happens if the LLM makes something up?** The prompt allows answers only from the retrieved context and requires citations; an output check replaces leaked prompts or harmful content; students can thumbs-down or report an answer, which goes to a moderation queue where an admin can fix the content or invalidate the cache.

**What about prompt injection?** Student text is cleaned and wrapped in delimiters in every prompt (current and earlier turns), the system prompt says text inside them is data, and an injection suite of 15 attacks runs in CI.

**Limitations?** Content is AI-assisted and needs expert review (every note is `reviewed: false` until a person checks it); free tiers sleep and rate-limit; the evaluation numbers depend on the real-model run; the study needs enough participants (about 64 per group for a medium effect at 80 % power).

**What would it cost at scale?** The free tiers cover a class. Beyond that the main cost is LLM tokens: the usage page shows tokens and estimated cost per request (a few thousand input tokens per answer). Caching identical first questions, the per-user quota and a global daily cap keep it bounded; paid Render and Aura tiers remove the sleep.

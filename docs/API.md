# Cognexa API

The FastAPI backend (`apps/api`) is the only thing the web app talks to besides Supabase Auth. This document has two parts: hand-written notes on conventions, errors and the streaming tutor (this part), and an endpoint reference generated from the running app (below the marker). The machine-readable contract is [`apps/web/src/lib/api-contract/openapi.json`](../apps/web/src/lib/api-contract/openapi.json), and the web app's request types are generated from it (`npm run api:types`). CI fails if either is stale.

Interactive docs: run the API locally and open `http://localhost:8000/docs`.

## Conventions

- **Base URL:** `NEXT_PUBLIC_API_URL` in the web app (local `http://localhost:8000`, production the Render URL).
- **Auth:** `Authorization: Bearer <Supabase access token>`. The API verifies the JWT against the project's JWKS (ES256/RS256/EdDSA; HS256 only when a legacy secret is configured) and loads the role from `public.profiles` (cached 30 s). Roles: `student` < `reviewer` < `admin`.
- **Request id:** send `X-Request-ID` (8-64 characters `[A-Za-z0-9._-]`) or the API makes one. It comes back as the `X-Request-ID` header and as `error.request_id`, and appears in every log line for that request.
- **Validation:** request bodies reject unknown fields (`extra = forbid`), and strings and lists have length limits (listed per endpoint below).
- **Subjects:** endpoints that read content take `subject_id` (default `dsa`); see [ADDING_A_SUBJECT.md](ADDING_A_SUBJECT.md).
- **Pagination:** list endpoints take `limit` (capped) and `offset` or a cursor where shown, and return `total` where it is cheap to count.
- **Compression:** JSON responses over about 1 KB are gzip-compressed when the client accepts it. The SSE stream is never compressed.

## Errors

Every error has the same shape (CLAUDE.md rule 7):

```json
{"error": {"code": "not_found", "message": "Chat thread not found.", "request_id": "3f2a...", "details": {"optional": "extra fields"}}}
```

`message` is safe to show to the user. `details` appears only where listed.

| HTTP | `code` | When |
|---|---|---|
| 400 | `scanned_pdf`, `empty_file`, `unsupported_file` | document upload (admin ingestion) cannot be read |
| 401 | `unauthorized` | missing, expired or invalid token |
| 403 | `forbidden` | role too low for the route |
| 403 | `account_disabled` | an admin disabled the account |
| 403 | `mode_not_allowed` | a student asked for `plain_rag` while `PLAIN_RAG_VISIBLE_TO_STUDENTS` is off |
| 404 | `not_found` | resource does not exist **or belongs to another user** (no existence leak) |
| 409 | `conflict` | e.g. regenerating an answer that is not the latest, a concurrent edit |
| 409 | `cycle_detected` | admin edge would create a prerequisite cycle; `details.path` is the blocking path |
| 409 | `already_answered`, `quiz_closed`, `time_up` | quiz state does not allow the action |
| 409 | `test_in_progress` | a study pre/post-test is open: no tutor, practice quiz or revision sheet until it is submitted |
| 409 | `not_available`, `study_off`, `nothing_due`, `nothing_to_revise` | the requested study step, review or sheet has nothing to work on |
| 409 | `partial_apply` | a proposal was applied to the graph but not to Postgres; retrying is safe (idempotent) |
| 413 | `INPUT_TOO_LONG`, `file_too_large` | text over `max_input_chars` (`details.max_input_chars`) or an upload over 10 MB |
| 422 | `validation_error`, `EMPTY_INPUT` | invalid body/path/query (first problem named in `message`), or text that is empty after cleaning |
| 429 | `QUOTA_EXCEEDED`, `RATE_LIMITED`, `GLOBAL_CAP` | AI usage guard (per-user daily quota, per-minute window, global daily cap) or a per-route rate limit; `Retry-After` header and `details.reset_at` / `details.retry_after_s` |
| 500 | `internal_error` | unexpected error (logged with the request id; no internals in the message) |
| 503 | `graph_unavailable` | Neo4j is down (the tutor itself falls back to plain RAG instead) |
| 503 | `llm_unavailable`, `embeddings_unavailable` | every LLM / embedding provider failed after retries and fallback |
| 503 | `auth_unavailable`, `database_not_configured`, `graph_not_configured` | a dependency is not configured or unreachable |
| 500 | `delete_failed` | account deletion could not remove the auth user |

AI requests (tutor messages, short-answer grading, revision sheets, admin suggestions) pass the **usage guard** once each. `GET /me/usage` returns today's use, the limits and `resets_at` (next UTC midnight).

## The streaming tutor (Server-Sent Events)

`POST /tutor/threads/{thread_id}/messages` (also `/tutor/messages/{id}/regenerate` and `/tutor/messages/{id}/edit`) answers with `Content-Type: text/event-stream`. Each event is an `event:` line and a JSON `data:` line, in this order:

| Event | When | `data` |
|---|---|---|
| `trace` | once, before any text | the retrieval trace: `mode`, `question`, `is_on_topic`, `intent`, `classification_path` (`llm` / `hybrid` / `continued` / `cache` / `none`), `matched[]` (`id`, `name`, `confidence`), `concepts[]` (role `matched` / `prerequisite` / `related`, `depth`, `weak`, `path`), `controller[]` (agentic steps), `diagnostic`, `chunks[]`, token budget, timings, `summary`, `degraded` (e.g. `graph_unavailable`) |
| `token` | many | `{"text": "..."}`: the next piece of the answer. Citations are `[[concept_id]]` markers inside the text. |
| `followups` | once, at the end of the text | `{"items": ["...", "..."]}`: suggested next questions |
| `done` | last, on success | `message_id`, `thread_id`, `content` (the final, moderated text: replace the streamed text with it), `moderated`, `cached`, `truncated`, `diagnostic` (true when the turn ended with a quick-check question), `usage` (`provider`, `model`, `tokens_in`, `tokens_out`, `latency_ms`, `model_calls`) |
| `error` | last, on failure | `code`, `message`, `message_id` (set when a partial answer was saved, so it can be regenerated) |

Behaviour worth knowing:

- Errors before the stream starts (auth, validation, quota, `test_in_progress`) are ordinary JSON error responses, not SSE.
- If the client disconnects, the server keeps the text sent so far as a `truncated` answer and still meters the model calls. If nothing was sent, the quota request is refunded.
- A quick-check question (`diagnostic: true`) ends the turn; the student's next message is treated as the reply and the turn continues with the stored trace.
- `POST /tutor/compare` (reviewer+) runs both modes on one question and returns JSON, not SSE.

## Health

- `GET /health`: process is up (no dependencies touched). Used by Render's health check.
- `GET /health/deep`: touches Postgres **and** Neo4j and reports each; `status` is `ok` or `degraded`. The daily keep-alive workflow calls it so the free tiers do not pause.

<!-- Everything below is generated by scripts/gen_api_docs.py; do not edit by hand. -->

## Endpoint reference

88 operations. **Access**: `public` needs no token, `signed in` needs a valid Supabase JWT, a role name means that role or higher (student < reviewer < admin). `?` marks an optional field.

### admin

| Method | Path | Access | Summary |
|---|---|---|---|
| PATCH | `/admin/content/chunks/{chunk_id}` | reviewer | Flag Chunk |
| PUT | `/admin/content/chunks/{chunk_id}` | reviewer | Edit Chunk |
| GET | `/admin/content/concepts/{concept_id}` | reviewer | Concept Content |
| PATCH | `/admin/content/questions/{question_id}` | reviewer | Flag Question |
| PUT | `/admin/content/questions/{question_id}` | reviewer | Edit Question |
| GET | `/admin/evaluation/runs` | reviewer | List Runs |
| GET | `/admin/evaluation/runs/{run_id}` | reviewer | Get Run |
| GET | `/admin/evaluation/runs/{run_id}/items` | reviewer | Run Items |
| GET | `/admin/feedback/by-concept` | reviewer | Thumbs Down By Concept |
| GET | `/admin/graph` | reviewer | Get Graph |
| POST | `/admin/graph/concepts` | reviewer | Create Concept |
| PUT | `/admin/graph/concepts/{concept_id}` | reviewer | Update Concept |
| POST | `/admin/graph/concepts/{concept_id}/suggest-edges` | reviewer | Suggest |
| DELETE | `/admin/graph/edges` | reviewer | Remove Edge |
| POST | `/admin/graph/edges` | reviewer | Add Edge |
| GET | `/admin/graph/edges/check` | reviewer | Check Edge |
| GET | `/admin/graph/export.yaml` | reviewer | Export Yaml |
| GET | `/admin/ingest` | reviewer | List Documents |
| POST | `/admin/ingest` | reviewer | Ingest |
| GET | `/admin/ingest/{document_id}` | reviewer | Get Document |
| POST | `/admin/llm/check` | admin | Llm Check |
| GET | `/admin/overview` | reviewer | Overview |
| GET | `/admin/proposals` | reviewer | List Proposals |
| GET | `/admin/proposals-count` | reviewer | Count Matching |
| POST | `/admin/proposals/bulk-approve` | reviewer | Bulk Approve |
| GET | `/admin/proposals/stats` | reviewer | Proposal Stats |
| GET | `/admin/proposals/{proposal_id}` | reviewer | Get Proposal |
| POST | `/admin/proposals/{proposal_id}/approve` | reviewer | Approve |
| POST | `/admin/proposals/{proposal_id}/reject` | reviewer | Reject |
| GET | `/admin/reports` | reviewer | List Reports |
| POST | `/admin/reports/{report_id}` | reviewer | Act On Report |
| POST | `/admin/reports/{report_id}/invalidate-cache` | reviewer | Invalidate Report Cache |
| GET | `/admin/settings` | admin | Get Admin Settings |
| PUT | `/admin/settings` | admin | Put Admin Settings |
| GET | `/admin/usage` | admin | Admin Usage |
| GET | `/admin/usage/export.csv` | admin | Usage Csv |
| GET | `/admin/users` | admin | List Users |
| PATCH | `/admin/users/{user_id}` | admin | Update User |
| GET | `/admin/users/{user_id}/usage` | admin | User Usage |

- **PATCH `/admin/content/chunks/{chunk_id}`**
  - body `Flags`:
    - `reviewed`?: boolean | null
    - `status`?: `active` | `inactive` | null
- **PUT `/admin/content/chunks/{chunk_id}`**
  - body `ChunkEdit`:
    - `heading`: string; min length 1, max length 200
    - `text`: string; min length 20, max length 12000
    - `kind`: string; max length 32
    - `reviewed`?: boolean | null
- **PATCH `/admin/content/questions/{question_id}`**
  - body `Flags`:
    - `reviewed`?: boolean | null
    - `status`?: `active` | `inactive` | null
- **PUT `/admin/content/questions/{question_id}`**
  - body `QuestionEdit`:
    - `type`: `mcq` | `multi_select` | `true_false` | `code_output` | `short_answer`
    - `difficulty`: integer
    - `prompt`: string
    - `code`?: string | null
    - `language`?: `python` | `cpp` (default `python`)
    - `options`?: object[] | null
    - `answer`: any
    - `explanation`: string
    - `rubric`?: object | null
    - `misconception_tag`?: string | null; max length 100
    - `diagnoses_prereq`?: string | null; max length 64
    - `reviewed`?: boolean | null
- **GET `/admin/evaluation/runs/{run_id}/items`**
  - query `category`?: string | null; max length 40
  - query `q`?: string | null; max length 100
- **GET `/admin/feedback/by-concept`**
  - query `days`?: integer; ≥ 1, ≤ 365
- **GET `/admin/graph`**
  - query `subject_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
- **POST `/admin/graph/concepts`**
  - query `subject_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
  - body `ConceptCreate`:
    - `name`: string; min length 1, max length 200
    - `cluster`: string; min length 1, max length 64, pattern `^[a-z][a-z0-9_]*$`
    - `difficulty`: integer; ≥ 1.0, ≤ 5.0
    - `description`: string; min length 10, max length 600
    - `aliases`?: string[]; max items 40
    - `keywords`?: string[]; max items 40
    - `order_index`?: integer | null; ≥ 0.0, ≤ 100000.0
    - `id`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
- **PUT `/admin/graph/concepts/{concept_id}`**
  - body `ConceptIn`:
    - `name`: string; min length 1, max length 200
    - `cluster`: string; min length 1, max length 64, pattern `^[a-z][a-z0-9_]*$`
    - `difficulty`: integer; ≥ 1.0, ≤ 5.0
    - `description`: string; min length 10, max length 600
    - `aliases`?: string[]; max items 40
    - `keywords`?: string[]; max items 40
    - `order_index`?: integer | null; ≥ 0.0, ≤ 100000.0
- **POST `/admin/graph/concepts/{concept_id}/suggest-edges`**
  - query `subject_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
- **DELETE `/admin/graph/edges`**
  - query `source`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
  - query `target`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
  - query `type`: `PREREQUISITE_OF` | `RELATED_TO`
  - query `rationale`?: string | null; max length 1000
- **POST `/admin/graph/edges`**
  - body `EdgeIn`:
    - `source`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
    - `target`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
    - `type`: `PREREQUISITE_OF` | `RELATED_TO`
    - `rationale`?: string | null; max length 1000
    - `weight`?: number (default `1.0`); ≥ 0.0, ≤ 1.0
- **GET `/admin/graph/edges/check`**
  - query `source`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
  - query `target`: string; pattern `^[a-z][a-z0-9_]{1,63}$`
- **GET `/admin/graph/export.yaml`**
  - query `subject_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
- **GET `/admin/ingest`**
  - query `limit`?: integer; ≥ 1, ≤ 100
- **POST `/admin/ingest`**
  - query `filename`: string; min length 1, max length 255
  - query `subject_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
- **POST `/admin/llm/check`**
  - body `LLMCheckIn`:
    - `prompt`?: string (default `Reply with the single word: ready`); min length 1, max length 200
- **GET `/admin/proposals`**
  - query `status`?: `pending` | `approved` | `rejected` | null
  - query `type`?: `add_edge` | `remove_edge` | `tag_chunk` | `new_concept` | null
  - query `min_confidence`?: number | null; ≥ 0, ≤ 1
  - query `document_id`?: string | null; max length 64
  - query `page`?: integer; ≥ 1, ≤ 1000
  - query `page_size`?: integer; ≥ 1, ≤ 100
- **GET `/admin/proposals-count`**
  - query `min_confidence`: number; ≥ 0.5, ≤ 1
  - query `type`?: `add_edge` | `remove_edge` | `tag_chunk` | `new_concept` | null
  - query `document_id`?: string | null; max length 64
- **POST `/admin/proposals/bulk-approve`**
  - body `BulkIn`:
    - `min_confidence`: number; ≥ 0.5, ≤ 1.0
    - `type`?: `add_edge` | `remove_edge` | `tag_chunk` | `new_concept` | null
    - `document_id`?: string | null; max length 64
    - `expected_count`: integer; ≥ 1.0, ≤ 500.0
    - `note`?: string | null; max length 1000
- **POST `/admin/proposals/{proposal_id}/approve`**
  - body `DecisionIn`:
    - `note`?: string | null; max length 1000
    - `edits`?: object | null
- **POST `/admin/proposals/{proposal_id}/reject`**
  - body `DecisionIn`:
    - `note`?: string | null; max length 1000
    - `edits`?: object | null
- **GET `/admin/reports`**
  - query `status`?: `open` | `reviewing` | `resolved` | `dismissed` | null
  - query `page`?: integer; ≥ 1, ≤ 1000
  - query `page_size`?: integer; ≥ 1, ≤ 50
- **POST `/admin/reports/{report_id}`**
  - body `ReportAction`:
    - `status`: `reviewing` | `resolved` | `dismissed`
    - `note`?: string | null; max length 2000
- **PUT `/admin/settings`**
  - body `SettingsIn`:
    - `quota`?: QuotaSettings | null
    - `role_multipliers`?: RoleMultipliers | null
    - `global_cap`?: GlobalCap | null
    - `cache`?: CacheSettings | null
    - `features`?: Features | null
    - `pricing`?: Pricing | null
- **GET `/admin/usage`**
  - query `days`?: integer; ≥ 1, ≤ 90
- **GET `/admin/usage/export.csv`**
  - query `days`?: integer; ≥ 1, ≤ 365
- **GET `/admin/users`**
  - query `q`?: string | null; max length 100
  - query `page`?: integer; ≥ 1, ≤ 10000
  - query `page_size`?: integer; ≥ 1, ≤ 100
- **PATCH `/admin/users/{user_id}`**
  - body `UserPatch`:
    - `role`?: `student` | `reviewer` | `admin` | null
    - `study_group`?: `adaptive` | `baseline` | `none` | null
    - `quota_override`?: QuotaOverride | null
    - `clear_quota_override`?: boolean (default `False`)
    - `disabled`?: boolean | null
- **GET `/admin/users/{user_id}/usage`**
  - query `days`?: integer; ≥ 1, ≤ 90

### concepts

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/concepts` | signed in | List Concepts |

- **GET `/concepts`**
  - query `subject_id`?: string | null; max length 50, pattern `^[a-z][a-z0-9_]*$`

### dashboard

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/dashboard` | signed in | Dashboard |
| GET | `/graph/mastery` | signed in | Graph Mastery |

- **GET `/dashboard`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`
- **GET `/graph/mastery`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`

### graph

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/graph` | public | Public Graph |

- **GET `/graph`**
  - query `subject_id`?: string | null; max length 50, pattern `^[a-z][a-z0-9_]*$`

### health

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/health` | public | Health |
| GET | `/health/deep` | public | Health Deep |

### learn

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/concepts/{concept_id}` | signed in | Concept Page |
| GET | `/me/mastery` | signed in | My Mastery |

- **GET `/me/mastery`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`

### me

| Method | Path | Access | Summary |
|---|---|---|---|
| DELETE | `/me` | signed in | Delete Me |
| GET | `/me` | signed in | Get Me |
| PATCH | `/me` | signed in | Patch Me |
| GET | `/me/export` | signed in | Export Me |
| POST | `/me/onboarding-complete` | signed in | Complete Onboarding |
| GET | `/me/usage` | signed in | Get My Usage |

- **DELETE `/me`**
  - body `DeleteIn`:
    - `confirm`: `DELETE`
- **PATCH `/me`**
  - body `MePatch`:
    - `display_name`?: string | null; min length 1, max length 80
    - `theme`?: `neon-noir` | `titanium-dark` | `titanium-light` | null
- **POST `/me/onboarding-complete`**
  - body `OnboardingIn`:
    - `experience_level`: `beginner` | `intermediate` | `advanced`

### notes

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/notes` | signed in | List Notes |
| DELETE | `/notes/{concept_id}` | signed in | Delete Note |
| GET | `/notes/{concept_id}` | signed in | Get Note |
| PUT | `/notes/{concept_id}` | signed in | Put Note |

- **GET `/notes`**
  - query `q`?: string | null; max length 100
  - query `cluster`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
  - query `bookmarked`?: boolean | null
- **PUT `/notes/{concept_id}`**
  - body `NoteIn`:
    - `body`?: string | null; max length 20000
    - `bookmarked`?: boolean | null

### quiz

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/quiz/history` | signed in | History |
| POST | `/quiz/sessions` | signed in | Create Session |
| GET | `/quiz/sessions/{session_id}` | signed in | Get Session |
| POST | `/quiz/sessions/{session_id}/answers` | signed in | Answer |
| POST | `/quiz/sessions/{session_id}/regrade` | signed in | Regrade |
| POST | `/quiz/sessions/{session_id}/submit` | signed in | Submit |

- **GET `/quiz/history`**
  - query `page`?: integer; ≥ 1, ≤ 10000
  - query `page_size`?: integer; ≥ 1, ≤ 100
- **POST `/quiz/sessions`**
  - body `SessionIn`:
    - `mode`: `concept` | `adaptive` | `review` | `diagnostic` | `pretest` | `posttest`
    - `subject_id`?: string (default `dsa`); pattern `^[a-z][a-z0-9_]{0,63}$`
    - `concept_id`?: string | null; pattern `^[a-z][a-z0-9_]{0,63}$`
    - `count`?: integer | null; ≥ 3.0, ≤ 20.0
    - `timed`?: boolean (default `False`)
    - `feedback_mode`?: `immediate` | `exam` (default `immediate`)
    - `question_ids`?: string[] | null; min items 1, max items 20
- **POST `/quiz/sessions/{session_id}/answers`**
  - body `AnswerIn`:
    - `question_id`: string; min length 1, max length 120
    - `response`?: string | boolean | string[] | null
    - `time_ms`?: integer | null; ≥ 0.0, ≤ 86400000.0
- **POST `/quiz/sessions/{session_id}/submit`**
  - body `SubmitIn`:
    - `responses`?: object

### recommendations

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/recommendations` | signed in | Recommendations |
| POST | `/recommendations/{log_id}/click` | signed in | Click |
| GET | `/review/due` | signed in | Review Due |

- **GET `/recommendations`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`
  - query `surface`?: `dashboard` | `tutor` | `quiz` | `review` | `learn`
  - query `limit`?: integer; ≥ 1, ≤ 3
- **GET `/review/due`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`

### revision

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/revision-sheets` | signed in | List Sheets |
| POST | `/revision-sheets` | signed in | Create Sheet |
| DELETE | `/revision-sheets/{sheet_id}` | signed in | Delete Sheet |
| GET | `/revision-sheets/{sheet_id}` | signed in | Get Sheet |

- **POST `/revision-sheets`**
  - body `SheetIn`:
    - `subject_id`?: string (default `dsa`); pattern `^[a-z][a-z0-9_]{0,63}$`
    - `concept_ids`?: string[] | null; min items 1, max items 5

### study

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/admin/study` | admin | Admin Study |
| PUT | `/admin/study` | admin | Update Study |
| GET | `/admin/study/export.csv` | admin | Export Csv |
| POST | `/study/consent` | signed in | Give Consent |
| GET | `/study/me` | signed in | My Study |
| POST | `/study/withdraw` | signed in | Withdraw |

- **PUT `/admin/study`**
  - body `StudyPatch`:
    - `enabled`?: boolean | null
    - `assignment`?: `random` | `alternate` | null
    - `posttest_unlock_at`?: string | null
    - `clear_unlock_date`?: boolean (default `False`)
    - `posttest_after_days`?: integer | null; ≥ 0.0, ≤ 365.0
    - `pretest_minutes`?: integer | null; ≥ 5.0, ≤ 120.0

### tutor

| Method | Path | Access | Summary |
|---|---|---|---|
| GET | `/tutor/chunks` | signed in | Chunks |
| POST | `/tutor/compare` | reviewer | Compare |
| POST | `/tutor/messages/{message_id}/edit` | signed in | Edit And Resend |
| POST | `/tutor/messages/{message_id}/feedback` | signed in | Feedback |
| POST | `/tutor/messages/{message_id}/regenerate` | signed in | Regenerate |
| GET | `/tutor/suggestions` | signed in | Suggestions |
| GET | `/tutor/threads` | signed in | List Threads |
| POST | `/tutor/threads` | signed in | Create Thread |
| DELETE | `/tutor/threads/{thread_id}` | signed in | Delete Thread |
| GET | `/tutor/threads/{thread_id}` | signed in | Get Thread |
| PATCH | `/tutor/threads/{thread_id}` | signed in | Patch Thread |
| POST | `/tutor/threads/{thread_id}/messages` | signed in | Post Message |

- **GET `/tutor/chunks`**
  - query `ids`: string[]; min items 1, max items 20
- **POST `/tutor/compare`**
  - body `CompareIn`:
    - `question`: string; min length 1, max length 8000
    - `subject_id`?: string (default `dsa`); pattern `^[a-z][a-z0-9_]{0,63}$`
    - `agentic`?: boolean (default `False`)
- **POST `/tutor/messages/{message_id}/edit`**
  - body `EditIn`:
    - `content`: string; min length 1, max length 8000
- **POST `/tutor/messages/{message_id}/feedback`**
  - body `FeedbackIn`:
    - `rating`?: `-1` | `0` | `1` | null
    - `report`?: ReportIn | null
- **GET `/tutor/suggestions`**
  - query `subject_id`?: string; pattern `^[a-z][a-z0-9_]{0,63}$`
- **GET `/tutor/threads`**
  - query `page`?: integer; ≥ 1, ≤ 10000
  - query `page_size`?: integer; ≥ 1, ≤ 100
  - query `archived`?: boolean
  - query `q`?: string | null; max length 100
- **POST `/tutor/threads`**
  - body `ThreadIn`:
    - `subject_id`?: string (default `dsa`); pattern `^[a-z][a-z0-9_]{0,63}$`
    - `title`?: string | null; min length 1, max length 200
- **PATCH `/tutor/threads/{thread_id}`**
  - body `ThreadPatch`:
    - `title`?: string | null; min length 1, max length 200
    - `archived`?: boolean | null
- **POST `/tutor/threads/{thread_id}/messages`**
  - body `MessageIn`:
    - `content`: string; min length 1, max length 8000
    - `mode`?: `graphrag` | `plain_rag` (default `graphrag`)

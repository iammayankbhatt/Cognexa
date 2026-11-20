# Cognexa architecture

> Written for: the project team, examiners and future maintainers. This file grows phase by
> phase; Phase 16 completes it with diagrams. Sections below are authoritative for the parts
> they cover.

## Mastery model (Phase 8)

Cognexa keeps one mastery score per student and concept, between 0 and 1, in the `mastery`
table. It is rule-based on purpose: every change can be explained to a student and checked by
hand, which matters for the user study (Report Objective 3). All constants live in
`apps/api/app/core/config.py` (`MASTERY_*`) and the formulas in `apps/api/app/mastery/model.py`.

### Update after each graded answer

For an answer on concept *c* with result *r* (0 to 1, partial credit allowed) to a question of
difficulty *d*:

| Difficulty *d* | Weight *w* |
|---|---|
| 1 | 0.8 |
| 2 | 1.0 |
| 3 | 1.2 |

```
score_c ← clamp(score_c + 0.3 · w · (r − score_c), 0, 1)
```

The score moves 30 % of the way toward the result (24 % for easy questions, 36 % for hard
ones), so one lucky or unlucky answer never dominates, and recent answers still count more than
old ones. Examples: a new student (0) answering a medium question correctly reaches 0.30; a
student at 0.50 who gets a medium question wrong drops to 0.35.

**Prerequisite signal.** Many questions name the prerequisite their typical mistake points to
(`diagnoses_prereq`, written with the question bank). If the result is below 0.5, that
prerequisite *p* also loses a little: `score_p ← max(0, score_p − 0.05)`. A correct answer leaves
*p* unchanged. This is how quiz mistakes feed the graph walk: the tutor and recommender then see
*p* as weak.

Each answer also increments `attempts` (and `correct` for a full score) and sets
`last_practiced_at`. Updates of one submission are applied in order inside one transaction, with
rows locked in concept-id order.

### Decay at read time

Knowledge fades without practice. The stored score never changes on its own; every read applies

```
effective = score · 0.98 ^ (days since last practised / 7)
```

about 2 % per week (a 0.80 score untouched for ten weeks reads as 0.65). Practising again
refreshes `last_practiced_at`. Everything that uses mastery (tutor personalisation, Smart quiz,
concept pages, dashboard) uses the effective score.

### Bands

| Effective score | Band | UI colour |
|---|---|---|
| < 0.40 | weak | `--danger` |
| 0.40 to 0.75 | developing | `--warning` |
| > 0.75 | strong | `--success` |

The tutor treats a prerequisite as *weak* when its effective score is below 0.6 or it was never
practised (`app/tutor/traverse.py`), a stricter line than the "weak" band because an explanation
should err on the side of covering the prerequisite.

### Where the numbers come from

- Smart quiz difficulty: effective < 0.4 → difficulty 1, 0.4–0.75 → 2, > 0.75 → 3.
- The onboarding diagnostic (10 easy questions across the eight clusters) creates the first
  mastery rows.
- Spaced review dates (`next_review_at`) are set by Phase 9.

## Quiz grading (Phase 8)

| Type | Rule |
|---|---|
| mcq, true_false | exact match |
| multi_select | `max(0, (correct chosen − wrong chosen) / total correct)`; duplicates count once |
| code_output | compare after normalising line endings, trailing spaces, case and trailing newlines |
| short_answer | judge model, JSON `{score, matched_points, missing_points, feedback}` against the rubric, temperature 0, one usage-guard request, cached by (question, normalised answer, model); if the judge is unavailable the answer is *pending* and graded on retry — submission is never blocked |

Every answer stores feedback: the explanation, the misconception of a chosen distractor, and for
results below 0.5 the diagnosed prerequisite ("This often means Call Stack needs review").
Timing is server-side: timed sessions refuse answers after the limit (plus 5 s grace).

## Questions-asked signal (Phase 8)

Each tutor question that was classified (not a continuation, not off-topic) logs its matched
concepts to `concept_interest (user, concept, source, asked_at)`. The Phase 9 recommender uses it
alongside quiz performance, as the report's abstract requires.

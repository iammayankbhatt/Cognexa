"""Quiz sessions end to end: choose questions, grade answers, update mastery.

Immediate mode: each answer is graded when it is sent (feedback right away) and mastery updates.
Exam mode: answers are stored ungraded and graded together on submit.
Short answers go to the judge model through the usage guard (1 request each); if that fails the
answer is "pending" and `regrade` grades it later. Submission is never blocked.
Timing is server-side: in timed sessions answers after started_at + limit (+ grace) are refused.
"""

from __future__ import annotations

import datetime as dt
import logging
import random
import uuid
from typing import Any, Literal

from app.auth.deps import CurrentUser
from app.cache.service import LLMCache
from app.core.config import Settings
from app.core.errors import AppError
from app.db.session import Database
from app.llm.errors import LLMError
from app.llm.router import LLMRouter
from app.llm.types import LLMResult
from app.mastery.model import MasteryParams
from app.mastery.repository import GradedEvent, MasteryRepository
from app.quiz import selection
from app.quiz.grading import Grade, InvalidResponseError, QuestionData, check_response, grade_auto
from app.quiz.judge import judge_short_answer, pending_grade, to_grade
from app.quiz.repository import QuizRepository
from app.recommender.engine import recommend
from app.recommender.service import build_graph, learner_state, mark_completed
from app.study.service import TEST_MODES, open_test
from app.tutor.suggest import SyllabusGraph
from app.usage.guard import UsageGuard

logger = logging.getLogger(__name__)

QuizMode = Literal["concept", "adaptive", "review", "diagnostic", "pretest", "posttest"]
FeedbackMode = Literal["immediate", "exam"]
MIN_COUNT, MAX_COUNT = 3, 20


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


class QuizService:
    def __init__(
        self,
        *,
        db: Database,
        settings: Settings,
        judge: LLMRouter,
        guard: UsageGuard,
        cache: LLMCache | None,
        graph: SyllabusGraph | None,
        rng: random.Random | None = None,
    ) -> None:
        self.db = db
        self.settings = settings
        self.judge = judge
        self.guard = guard
        self.cache = cache
        self.graph = graph
        self.rng = rng or random.Random()
        self.params = MasteryParams.from_settings(settings)

    # ---------------------------------------------------------------- create
    async def create(
        self,
        user: CurrentUser,
        *,
        mode: QuizMode,
        subject_id: str,
        concept_id: str | None = None,
        count: int | None = None,
        timed: bool = False,
        feedback_mode: FeedbackMode = "immediate",
        question_ids: list[str] | None = None,
    ) -> dict[str, Any]:
        n = max(MIN_COUNT, min(MAX_COUNT, count or self.settings.quiz_default_count))
        reserved = selection.reserved_ids(subject_id) if mode not in TEST_MODES else frozenset()
        async with self.db.sessions()() as session:
            repo = QuizRepository(session)
            if mode not in TEST_MODES and await open_test(session, user.id):
                # practice answers would reveal keys while a study test is open (BUG-050)
                raise AppError(
                    "test_in_progress", "Finish your study test first, then practise.", 409
                )
            seen = await repo.recently_seen(user.id, self.settings.quiz_no_repeat_days)
            effective = await MasteryRepository(session, self.params).effective_map(
                user.id, subject_id
            )
            picked: list[QuestionData]
            if question_ids:
                if mode != "concept":
                    raise AppError("validation_error", "A question list needs concept mode.", 422)
                # active, in-subject, non-reserved questions only (BUG-050, BUG-051)
                found = {
                    q.id: q
                    for q in await repo.questions(subject_id, ids=question_ids, exclude=reserved)
                }
                picked = [found[i] for i in dict.fromkeys(question_ids) if i in found]
            elif mode == "concept":
                if not concept_id:
                    raise AppError("validation_error", "Choose a concept for this quiz.", 422)
                pool = await repo.questions(subject_id, concept_ids=[concept_id], exclude=reserved)
                if not pool:
                    raise AppError("not_found", "No questions for this concept yet.", 404)
                picked = selection.for_concept(pool, seen, n, self.rng)
            elif mode == "adaptive":
                order = [c["id"] for c in await repo.concept_rows(subject_id)]
                nxt = None
                if self.graph is not None:
                    # The recommender's next best step joins the weakest concepts (Phase 9).
                    graph = await build_graph(self.graph, subject_id)
                    state = await learner_state(session, user.id, subject_id, self.params, _now())
                    top = recommend(graph, state, 1)
                    nxt = top[0].concept_id if top else None
                targets = selection.adaptive_concepts(effective, nxt, order)
                pool = await repo.questions(subject_id, concept_ids=targets, exclude=reserved)
                picked = selection.for_adaptive(pool, targets, effective, seen, n, self.rng)
            elif mode == "diagnostic":
                pool = await repo.questions(
                    subject_id, types=selection.AUTO_TYPES, exclude=reserved
                )
                picked = selection.for_diagnostic(
                    pool, await repo.concept_rows(subject_id), self.rng
                )
            elif mode == "review":
                due = await repo.due_concepts(user.id, subject_id, _now())
                if not due:
                    raise AppError("nothing_due", "Nothing is due for review right now.", 409)
                pool = await repo.questions(subject_id, concept_ids=due[:n], exclude=reserved)
                picked = selection.prefer_unseen(pool, seen, n, self.rng)
            else:  # pretest / posttest: fixed forms, in file order
                ids = selection.study_set(subject_id, mode)
                found = await repo.questions_by_id(ids)
                picked = [found[i] for i in ids if i in found]
            if not picked:
                raise AppError("not_found", "No questions are available for this quiz.", 404)
        if mode in ("diagnostic", "pretest", "posttest"):
            feedback_mode = "exam"  # no feedback before the end on placement and study tests
        limit = len(picked) * self.settings.quiz_seconds_per_question if timed else None
        async with self.db.sessions()() as session, session.begin():
            row = await QuizRepository(session).create_session(
                user_id=user.id, subject_id=subject_id, mode=mode, concept_id=concept_id,
                time_limit_s=limit, question_ids=[q.id for q in picked],
                feedback_mode=feedback_mode,
            )  # fmt: skip
        return self._session_view(row, picked, [], {})

    # ---------------------------------------------------------------- answer
    async def answer(
        self,
        user: CurrentUser,
        session_id: uuid.UUID,
        question_id: str,
        response: Any,
        time_ms: int | None = None,
    ) -> dict[str, Any]:
        sess, questions = await self._open(user, session_id)
        q = questions.get(question_id)
        if q is None:
            raise AppError("not_found", "That question is not part of this quiz.", 404)
        try:
            value = check_response(q, response)
        except InvalidResponseError as e:
            raise AppError("validation_error", str(e), 422) from e
        if sess["feedback_mode"] == "exam":
            async with self.db.sessions()() as session, session.begin():
                await self._lock_open(QuizRepository(session), user, session_id)
                await QuizRepository(session).save_answer(
                    session_id=session_id, user_id=user.id, question_id=q.id,
                    response={"value": value}, time_ms=time_ms, is_correct=None, score=None,
                    feedback=None, pending=False,
                )  # fmt: skip
            return {"question_id": q.id, "saved": True}
        async with self.db.sessions()() as session:
            prior = {a["question_id"]: a for a in await QuizRepository(session).answers(session_id)}
        if q.id in prior and prior[q.id]["score"] is not None:
            # checked again under the lock below; this early check saves a judge request (BUG-049)
            raise AppError("already_answered", "You already answered this question.", 409)
        grade = await self._grade(user, q, value)
        async with self.db.sessions()() as session, session.begin():
            repo = QuizRepository(session)
            # Serialise answers per session (BUG-047): without the row lock, concurrent answers to
            # one question all passed the check below and applied the mastery update twice.
            await self._lock_open(repo, user, session_id)
            previous = {a["question_id"]: a for a in await repo.answers(session_id)}
            if q.id in previous and previous[q.id]["score"] is not None:
                raise AppError("already_answered", "You already answered this question.", 409)
            row = await repo.save_answer(
                **self._answer_values(user, session_id, q, value, grade, time_ms)
            )
            names = await repo.concept_names([q.diagnoses_prereq or ""])
            if grade.score is not None:
                await MasteryRepository(session, self.params).apply(
                    user.id, sess["subject_id"], [self._event(q, grade)]
                )
        return self._answer_view(q, row, reveal=True, names=names)

    # ---------------------------------------------------------------- submit
    async def submit(
        self, user: CurrentUser, session_id: uuid.UUID, responses: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        """Finish the quiz. In exam mode, `responses` (question id -> answer) may carry answers not
        sent one by one; everything ungraded is graded now. Unanswered questions score 0."""
        sess, questions = await self._load(user, session_id)
        if sess["submitted_at"] is not None:
            return await self.get(user, session_id)
        late = self._is_late(sess)
        async with self.db.sessions()() as session:
            existing = {
                a["question_id"]: a for a in await QuizRepository(session).answers(session_id)
            }
        incoming: dict[str, Any] = {}
        if responses and not late:
            for qid, resp in responses.items():
                if qid not in questions:
                    raise AppError("not_found", f"Question {qid} is not part of this quiz.", 404)
                try:
                    incoming[qid] = check_response(questions[qid], resp)
                except InvalidResponseError as e:
                    raise AppError("validation_error", f"{qid}: {e}", 422) from e
        graded: list[tuple[QuestionData, Any, Grade, int | None]] = []
        for qid in sess["question_ids"]:
            q = questions.get(qid)
            if q is None:
                continue
            prev = existing.get(qid)
            if prev is not None and prev["score"] is not None and not prev["pending"]:
                continue  # already graded (immediate mode)
            if qid in incoming:
                value, t = incoming[qid], None
            elif prev is not None:
                value, t = prev["response"].get("value"), prev["time_ms"]
            else:
                value, t = None, None
            graded.append((q, value, await self._grade(user, q, value), t))
        now = _now()
        async with self.db.sessions()() as session, session.begin():
            repo = QuizRepository(session)
            locked = await repo.get_session(user.id, session_id, lock=True)
            if locked is None or locked["submitted_at"] is not None:
                pass  # submitted concurrently: the other request already finished it
            else:
                # An immediate-mode answer may have been graded after `existing` was read (it
                # waited on this row lock); keep that grade, never grade a question twice (BUG-047).
                fresh = {a["question_id"]: a for a in await repo.answers(session_id)}
                graded = [
                    item
                    for item in graded
                    if not (
                        (f := fresh.get(item[0].id)) is not None
                        and f["score"] is not None
                        and not f["pending"]
                    )
                ]
                for q, value, grade, t in graded:
                    await repo.save_answer(
                        **self._answer_values(user, session_id, q, value, grade, t)
                    )
                events = [self._event(q, g) for q, _, g, _ in graded if g.score is not None]
                await MasteryRepository(session, self.params).apply(
                    user.id, sess["subject_id"], events
                )
                answers = await repo.answers(session_id)
                score = sum(float(a["score"] or 0) for a in answers)
                await repo.finish_session(
                    session_id, round(score, 3), float(len(sess["question_ids"])), now
                )
                await self._after_submit(session, user, sess, questions, answers, now)
        return await self.get(user, session_id)

    # ---------------------------------------------------------------- regrade
    async def regrade(self, user: CurrentUser, session_id: uuid.UUID) -> dict[str, Any]:
        """Grade answers still pending (the judge was unavailable before)."""
        sess, questions = await self._load(user, session_id)
        async with self.db.sessions()() as session:
            pending = [a for a in await QuizRepository(session).answers(session_id) if a["pending"]]
        for a in pending:
            q = questions.get(a["question_id"])
            if q is None:
                continue
            value = a["response"].get("value")
            grade = await self._grade(user, q, value)
            if grade.pending:
                continue
            async with self.db.sessions()() as session, session.begin():
                repo = QuizRepository(session)
                locked = await repo.get_session(user.id, session_id, lock=True)
                current = {x["question_id"]: x for x in await repo.answers(session_id)}
                if locked is None or not (c := current.get(q.id)) or not c["pending"]:
                    continue  # a concurrent regrade (or submit) graded it already (BUG-047)
                await repo.save_answer(
                    **self._answer_values(user, session_id, q, value, grade, a["time_ms"])
                )
                await MasteryRepository(session, self.params).apply(
                    user.id, sess["subject_id"], [self._event(q, grade)]
                )
                if locked["submitted_at"] is not None:
                    answers = await repo.answers(session_id)
                    await repo.set_score(
                        session_id, round(sum(float(x["score"] or 0) for x in answers), 3)
                    )
                    # completion depends on the final scores (BUG-048); the review schedule is
                    # left as set at submit (LIM-043)
                    await self._complete_passed(session, user, sess, questions, answers)
        return await self.get(user, session_id)

    # ---------------------------------------------------------------- read
    async def get(self, user: CurrentUser, session_id: uuid.UUID) -> dict[str, Any]:
        sess, questions = await self._load(user, session_id)
        async with self.db.sessions()() as session:
            answers = {
                a["question_id"]: a for a in await QuizRepository(session).answers(session_id)
            }
            names = await QuizRepository(session).concept_names(
                {q.concept_id for q in questions.values()}
                | {q.diagnoses_prereq for q in questions.values() if q.diagnoses_prereq}
            )
        ordered = [questions[i] for i in sess["question_ids"] if i in questions]
        return self._session_view(sess, ordered, list(answers.values()), names)

    async def history(self, user: CurrentUser, page: int, page_size: int) -> dict[str, Any]:
        async with self.db.sessions()() as session:
            rows, total = await QuizRepository(session).history(
                user.id, page_size, (page - 1) * page_size
            )
        items = [
            {
                "id": str(r["id"]),
                "mode": str(r["mode"]),
                "concept_id": r["concept_id"],
                "concept_name": r["concept_name"],
                "started_at": r["started_at"],
                "submitted_at": r["submitted_at"],
                "score": float(r["score"]) if r["score"] is not None else None,
                "max_score": float(r["max_score"]) if r["max_score"] is not None else None,
                "questions": len(r["question_ids"]),
            }
            for r in rows
        ]
        return {"items": items, "page": page, "page_size": page_size, "total": total}

    # ---------------------------------------------------------------- internals
    async def _after_submit(
        self,
        session: Any,
        user: CurrentUser,
        sess: dict[str, Any],
        questions: dict[str, QuestionData],
        answers: list[dict[str, Any]],
        now: dt.datetime,
    ) -> None:
        """Spaced review for every concept in the quiz (not on study tests) and completion of
        recommendations for concepts passed with >= 60 %."""
        ratios = self._concept_ratios(sess, questions, answers)
        if str(sess["mode"]) not in ("pretest", "posttest"):
            await MasteryRepository(session, self.params).schedule_reviews(user.id, ratios, now)
        await mark_completed(session, user.id, [c for c, r in ratios.items() if r >= 0.6], now)

    async def _complete_passed(
        self,
        session: Any,
        user: CurrentUser,
        sess: dict[str, Any],
        questions: dict[str, QuestionData],
        answers: list[dict[str, Any]],
    ) -> None:
        """Mark recommendations completed for concepts now passed with >= 60 % (idempotent)."""
        ratios = self._concept_ratios(sess, questions, answers)
        await mark_completed(session, user.id, [c for c, r in ratios.items() if r >= 0.6], _now())

    @staticmethod
    def _concept_ratios(
        sess: dict[str, Any], questions: dict[str, QuestionData], answers: list[dict[str, Any]]
    ) -> dict[str, float]:
        """Score / question count per concept; unanswered questions count as 0."""
        totals: dict[str, list[float]] = {}
        by_q = {a["question_id"]: a for a in answers}
        for qid in sess["question_ids"]:
            q = questions.get(qid)
            if q is None:
                continue
            a = by_q.get(qid)
            t = totals.setdefault(q.concept_id, [0.0, 0.0])
            t[0] += float(a["score"] or 0) if a else 0.0
            t[1] += 1
        return {c: got / n for c, (got, n) in totals.items() if n}

    async def _load(
        self, user: CurrentUser, session_id: uuid.UUID
    ) -> tuple[dict[str, Any], dict[str, QuestionData]]:
        async with self.db.sessions()() as session:
            repo = QuizRepository(session)
            sess = await repo.get_session(user.id, session_id)
            if sess is None:
                raise AppError("not_found", "Quiz not found.", 404)
            questions = await repo.questions_by_id(sess["question_ids"])
        return sess, questions

    async def _open(
        self, user: CurrentUser, session_id: uuid.UUID
    ) -> tuple[dict[str, Any], dict[str, QuestionData]]:
        sess, questions = await self._load(user, session_id)
        if sess["submitted_at"] is not None:
            raise AppError("quiz_closed", "This quiz has already been submitted.", 409)
        if self._is_late(sess):
            raise AppError(
                "time_up", "Time is up for this quiz. Submit it to see your results.", 409
            )
        return sess, questions

    async def _lock_open(
        self, repo: QuizRepository, user: CurrentUser, session_id: uuid.UUID
    ) -> None:
        """Lock the session row for this transaction and re-check that it is still open (a submit
        may have finished it since `_open` read it)."""
        locked = await repo.get_session(user.id, session_id, lock=True)
        if locked is None:
            raise AppError("not_found", "Quiz not found.", 404)
        if locked["submitted_at"] is not None:
            raise AppError("quiz_closed", "This quiz has already been submitted.", 409)

    def _is_late(self, sess: dict[str, Any]) -> bool:
        limit = sess["time_limit_s"]
        if not limit:
            return False
        deadline = sess["started_at"] + dt.timedelta(
            seconds=limit + self.settings.quiz_time_grace_s
        )
        late: bool = _now() > deadline
        return late

    async def _grade(self, user: CurrentUser, q: QuestionData, value: Any) -> Grade:
        async with self.db.sessions()() as session:
            names = await QuizRepository(session).concept_names([q.diagnoses_prereq or ""])
        prereq_name = names.get(q.diagnoses_prereq or "")
        if q.type != "short_answer":
            return grade_auto(q, value, prereq_name)
        if value is None or not str(value).strip():
            g = grade_auto_empty(q)
            return g
        results: list[LLMResult] = []
        try:
            async with self.guard.request(user, str(value), purpose="grading") as ticket:
                try:
                    judged = await judge_short_answer(
                        q, str(value), self.judge, self.cache, results
                    )
                finally:
                    for r in results:
                        await ticket.record(r)
                if not results:
                    await ticket.mark_cached()
        except (LLMError, AppError) as e:
            # Provider down or quota exhausted: keep the answer, grade it later.
            logger.info("short answer %s left pending: %s", q.id, e)
            return pending_grade()
        return to_grade(q, judged, prereq_name)

    @staticmethod
    def _event(q: QuestionData, g: Grade) -> GradedEvent:
        return GradedEvent(
            concept_id=q.concept_id,
            result=float(g.score or 0),
            difficulty=q.difficulty,
            diagnoses_prereq=q.diagnoses_prereq,
        )

    @staticmethod
    def _answer_values(
        user: CurrentUser,
        session_id: uuid.UUID,
        q: QuestionData,
        value: Any,
        g: Grade,
        time_ms: int | None,
    ) -> dict[str, Any]:
        return {
            "session_id": session_id,
            "user_id": user.id,
            "question_id": q.id,
            "response": {"value": value},
            "is_correct": g.is_correct,
            "score": g.score,
            "feedback": g.feedback,
            "graded_by": g.graded_by,
            "time_ms": time_ms,
            "pending": g.pending,
            "details": {**(g.details or {}), "misconceptions": g.misconceptions,
                        "diagnoses_prereq": g.diagnoses_prereq},
        }  # fmt: skip

    @staticmethod
    def _answer_view(
        q: QuestionData,
        a: dict[str, Any],
        *,
        reveal: bool,
        names: dict[str, str] | None = None,
    ) -> dict[str, Any]:
        details = a.get("details") or {}
        prereq = details.get("diagnoses_prereq")
        graded = a["score"] is not None or a["pending"]
        return {
            "question_id": q.id,
            "response": (a.get("response") or {}).get("value"),
            "score": float(a["score"]) if a["score"] is not None else None,
            "is_correct": a["is_correct"],
            "pending": a["pending"],
            "feedback": a["feedback"] if graded else None,
            "correct_answer": q.answer if reveal and graded else None,
            "diagnoses_prereq": prereq,
            "diagnoses_prereq_name": (names or {}).get(prereq) if prereq else None,
            "matched_points": details.get("matched_points"),
            "missing_points": details.get("missing_points"),
        }

    def _session_view(
        self,
        sess: dict[str, Any],
        ordered: list[QuestionData],
        answers: list[dict[str, Any]],
        names: dict[str, str],
    ) -> dict[str, Any]:
        submitted = sess["submitted_at"] is not None
        by_q = {a["question_id"]: a for a in answers}
        immediate = sess["feedback_mode"] == "immediate"
        items = []
        for q in ordered:
            item = {**q.public(), "concept_name": names.get(q.concept_id)}
            a = by_q.get(q.id)
            if a is not None:
                item["answer"] = self._answer_view(q, a, reveal=submitted or immediate, names=names)
                if not (submitted or immediate):  # exam mode before submit: no grades
                    item["answer"] = {"question_id": q.id, "response": item["answer"]["response"]}
            else:
                item["answer"] = None
            if submitted:
                item["explanation"] = q.explanation
            items.append(item)
        per_concept: dict[str, dict[str, Any]] = {}
        if submitted:
            for q in ordered:
                a = by_q.get(q.id)
                pc = per_concept.setdefault(
                    q.concept_id,
                    {"concept_id": q.concept_id, "name": names.get(q.concept_id, q.concept_id),
                     "score": 0.0, "max": 0.0},
                )  # fmt: skip
                pc["score"] += float(a["score"] or 0) if a else 0.0
                pc["max"] += 1
        weak_prereqs = sorted(
            {str(d) for a in answers if (d := (a.get("details") or {}).get("diagnoses_prereq"))}
        )
        deadline = (
            sess["started_at"] + dt.timedelta(seconds=sess["time_limit_s"])
            if sess["time_limit_s"]
            else None
        )
        return {
            "id": str(sess["id"]),
            "mode": str(sess["mode"]),
            "subject_id": sess["subject_id"],
            "concept_id": sess["concept_id"],
            "feedback_mode": sess["feedback_mode"],
            "started_at": sess["started_at"],
            "deadline": deadline,
            "submitted_at": sess["submitted_at"],
            "score": float(sess["score"]) if sess["score"] is not None else None,
            "max_score": float(sess["max_score"]) if sess["max_score"] is not None else None,
            "pending": sum(1 for a in answers if a["pending"]),
            "questions": items,
            "per_concept": [{**v, "score": round(v["score"], 3)} for v in per_concept.values()],
            "weak_prerequisites": [
                {"concept_id": c, "name": names.get(c, c)} for c in weak_prereqs
            ],
        }


def grade_auto_empty(q: QuestionData) -> Grade:
    return Grade(
        score=0.0,
        is_correct=False,
        feedback=q.explanation,
        graded_by="auto",
        diagnoses_prereq=q.diagnoses_prereq,
    )

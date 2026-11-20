"""User-study mode (Objective 5): enrolment, group assignment, test gating, anonymised export.

Flow for a student while STUDY_MODE is on:
    consent -> pretest (form A, auto-graded, timed) -> learning (recommendations follow the
    group) -> posttest (form B, unlocked by the admin date or N days after enrolment) -> complete
Withdrawing at any time removes the student from the study (group reset, excluded from export).
Assignment: "random" balances the two groups (the smaller group gets the next student, ties are
random); "alternate" alternates by enrolment order.
"""

from __future__ import annotations

import datetime as dt
import hashlib
import random
import uuid
from collections.abc import Callable
from typing import Any

from sqlalchemy import and_, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from app.db.tables import (
    chat_messages,
    profiles,
    quiz_answers,
    quiz_sessions,
    recommendations_log,
    study_settings,
)

GROUPS = ("adaptive", "baseline")
TEST_MODES = ("pretest", "posttest")


def _now() -> dt.datetime:
    return dt.datetime.now(dt.UTC)


async def load_settings(session: AsyncSession) -> dict[str, Any]:
    row = (await session.execute(select(study_settings).where(study_settings.c.id == 1))).first()
    if row is None:  # migrations insert it; defensive for odd databases
        return {
            "enabled": False,
            "assignment": "random",
            "posttest_unlock_at": None,
            "posttest_after_days": 14,
            "pretest_minutes": 20,
            "export_salt": "unset",
        }
    return dict(row._mapping)


def pick_group(
    counts: dict[str, int], assignment: str, rng: Callable[[], float] = random.random
) -> str:
    """Balanced random (smaller group first, ties by coin flip) or alternate by enrolment count."""
    a, b = counts.get("adaptive", 0), counts.get("baseline", 0)
    if assignment == "alternate":
        return GROUPS[(a + b) % 2]
    if a != b:
        return "adaptive" if a < b else "baseline"
    return GROUPS[0] if rng() < 0.5 else GROUPS[1]


async def group_counts(session: AsyncSession) -> dict[str, int]:
    rows = await session.execute(
        select(profiles.c.study_group, func.count())
        .where(profiles.c.study_enrolled_at.is_not(None), profiles.c.study_withdrawn_at.is_(None))
        .group_by(profiles.c.study_group)
    )
    return {str(g): int(n) for g, n in rows}


async def test_sessions(session: AsyncSession, user_id: uuid.UUID) -> dict[str, dict[str, Any]]:
    """Latest pretest / posttest session per mode."""
    rows = await session.execute(
        select(quiz_sessions)
        .where(quiz_sessions.c.user_id == user_id, quiz_sessions.c.mode.in_(TEST_MODES))
        .order_by(quiz_sessions.c.started_at)
    )
    out: dict[str, dict[str, Any]] = {}
    for r in rows:
        out[str(r.mode)] = dict(r._mapping)
    return out


def posttest_unlock_at(
    settings: dict[str, Any], enrolled_at: dt.datetime | None
) -> dt.datetime | None:
    """The earlier of the admin date and enrolment + N days (whichever exists)."""
    candidates = [d for d in (settings.get("posttest_unlock_at"),) if d is not None]
    if enrolled_at is not None:
        candidates.append(
            enrolled_at + dt.timedelta(days=int(settings.get("posttest_after_days") or 0))
        )
    return min(candidates) if candidates else None


def _test_view(s: dict[str, Any] | None) -> dict[str, Any] | None:
    if s is None:
        return None
    return {
        "session_id": str(s["id"]),
        "submitted": s["submitted_at"] is not None,
        "score": float(s["score"]) if s["score"] is not None else None,
        "max_score": float(s["max_score"]) if s["max_score"] is not None else None,
    }


async def study_state(
    session: AsyncSession, profile: dict[str, Any], enabled: bool, now: dt.datetime | None = None
) -> dict[str, Any]:
    now = now or _now()
    settings = await load_settings(session)
    user_id = profile["id"]
    tests = await test_sessions(session, user_id)
    pre, post = tests.get("pretest"), tests.get("posttest")
    unlock = posttest_unlock_at(settings, profile.get("study_enrolled_at"))
    if not enabled or profile.get("role") != "student":
        step = "off"
    elif profile.get("study_withdrawn_at"):
        step = "withdrawn"
    elif not profile.get("study_consent_at"):
        step = "consent"
    elif not (pre and pre["submitted_at"]):
        step = "pretest"
    elif post and post["submitted_at"]:
        step = "complete"
    elif unlock is not None and now >= unlock:
        step = "posttest"
    else:
        step = "learning"
    return {
        "enabled": enabled,
        "step": step,
        "group": str(profile.get("study_group") or "none"),
        "enrolled_at": profile.get("study_enrolled_at"),
        "consent_at": profile.get("study_consent_at"),
        "pretest": _test_view(pre),
        "posttest": _test_view(post),
        "posttest_unlock_at": unlock,
        "pretest_minutes": int(settings.get("pretest_minutes") or 20),
    }


async def consent(
    session: AsyncSession, user_id: uuid.UUID, rng: Callable[[], float] = random.random
) -> str:
    """Record consent, enrol and assign a group (once). Must run in a transaction."""
    row = (
        await session.execute(select(profiles).where(profiles.c.id == user_id).with_for_update())
    ).first()
    if row is None:
        raise LookupError("profile not found")
    if row.study_consent_at is not None and row.study_withdrawn_at is None:
        return str(row.study_group)
    settings = await load_settings(session)
    # Serialise assignments so two simultaneous consents cannot unbalance the groups.
    await session.execute(
        select(study_settings.c.id).where(study_settings.c.id == 1).with_for_update()
    )
    group = pick_group(await group_counts(session), str(settings["assignment"]), rng)
    now = _now()
    await session.execute(
        update(profiles)
        .where(profiles.c.id == user_id)
        .values(
            study_group=group, study_consent_at=now, study_enrolled_at=now, study_withdrawn_at=None
        )
    )
    return group


async def withdraw(session: AsyncSession, user_id: uuid.UUID) -> None:
    await session.execute(
        update(profiles)
        .where(profiles.c.id == user_id)
        .values(study_withdrawn_at=_now(), study_group="none")
    )


async def open_test(
    session: AsyncSession, user_id: uuid.UUID, now: dt.datetime | None = None
) -> bool:
    """True while the student has an unsubmitted, unexpired pretest or posttest (no AI then)."""
    now = now or _now()
    rows = await session.execute(
        select(quiz_sessions.c.started_at, quiz_sessions.c.time_limit_s).where(
            quiz_sessions.c.user_id == user_id,
            quiz_sessions.c.mode.in_(TEST_MODES),
            quiz_sessions.c.submitted_at.is_(None),
        )
    )
    for started, limit in rows:
        if limit is None or started + dt.timedelta(seconds=int(limit)) > now:
            return True
    return False


def participant_id(salt: str, user_id: uuid.UUID) -> str:
    return hashlib.sha256(f"{salt}:{user_id}".encode()).hexdigest()[:16]


def gain(pre: float | None, post: float | None, maximum: float | None) -> float | None:
    if pre is None or post is None or not maximum or maximum <= pre:
        return None
    return round((post - pre) / (maximum - pre), 4)


EXPORT_COLUMNS = [
    "participant",
    "group",
    "pretest",
    "posttest",
    "max_score",
    "normalized_gain",
    "quizzes_taken",
    "tutor_questions",
    "recommendations_shown",
    "recommendations_clicked",
    "recommendations_completed",
    "active_days",
]


async def export_rows(session: AsyncSession) -> list[dict[str, Any]]:
    """One anonymised row per enrolled, non-withdrawn participant (no names, no emails)."""
    settings = await load_settings(session)
    people = (
        await session.execute(
            select(profiles.c.id, profiles.c.study_group).where(
                profiles.c.study_enrolled_at.is_not(None), profiles.c.study_withdrawn_at.is_(None)
            )
        )
    ).all()
    out = []
    for pid, group in people:
        tests = await test_sessions(session, pid)
        pre, post = tests.get("pretest"), tests.get("posttest")
        pre_score = (
            float(pre["score"])
            if pre and pre["submitted_at"] and pre["score"] is not None
            else None
        )
        post_score = (
            float(post["score"])
            if post and post["submitted_at"] and post["score"] is not None
            else None
        )
        maximum = float(pre["max_score"]) if pre and pre["max_score"] else None

        async def count(q: Any) -> int:
            return int((await session.execute(q)).scalar_one())

        quizzes = await count(
            select(func.count())
            .select_from(quiz_sessions)
            .where(
                quiz_sessions.c.user_id == pid,
                quiz_sessions.c.submitted_at.is_not(None),
                quiz_sessions.c.mode.not_in(TEST_MODES),
            )
        )
        questions = await count(
            select(func.count())
            .select_from(chat_messages)
            .where(chat_messages.c.user_id == pid, chat_messages.c.role == "user")
        )
        log = recommendations_log.c
        shown = await count(
            select(func.count()).select_from(recommendations_log).where(log.user_id == pid)
        )
        clicked = await count(
            select(func.count())
            .select_from(recommendations_log)
            .where(and_(log.user_id == pid, log.clicked_at.is_not(None)))
        )
        completed = await count(
            select(func.count())
            .select_from(recommendations_log)
            .where(and_(log.user_id == pid, log.completed_at.is_not(None)))
        )
        days = await count(
            select(func.count(func.distinct(func.date(quiz_answers.c.created_at)))).where(
                quiz_answers.c.user_id == pid
            )
        )
        out.append(
            {
                "participant": participant_id(str(settings["export_salt"]), pid),
                "group": str(group),
                "pretest": pre_score,
                "posttest": post_score,
                "max_score": maximum,
                "normalized_gain": gain(pre_score, post_score, maximum),
                "quizzes_taken": quizzes,
                "tutor_questions": questions,
                "recommendations_shown": shown,
                "recommendations_clicked": clicked,
                "recommendations_completed": completed,
                "active_days": days,
            }
        )
    out.sort(key=lambda r: (r["group"], r["participant"]))
    return out


async def funnel(session: AsyncSession) -> dict[str, dict[str, int]]:
    """Per group: enrolled, pretest done, posttest done; plus withdrawn overall."""
    result: dict[str, dict[str, int]] = {
        g: {"enrolled": 0, "pretest": 0, "posttest": 0} for g in GROUPS
    }
    people = (
        await session.execute(
            select(profiles.c.id, profiles.c.study_group).where(
                profiles.c.study_enrolled_at.is_not(None), profiles.c.study_withdrawn_at.is_(None)
            )
        )
    ).all()
    for pid, group in people:
        g = str(group)
        if g not in result:
            continue
        result[g]["enrolled"] += 1
        tests = await test_sessions(session, pid)
        for mode in TEST_MODES:
            if tests.get(mode) and tests[mode]["submitted_at"]:
                result[g][mode] += 1
    withdrawn = (
        await session.execute(
            select(func.count())
            .select_from(profiles)
            .where(profiles.c.study_withdrawn_at.is_not(None))
        )
    ).scalar_one()
    result["withdrawn"] = {"count": int(withdrawn)}
    return result

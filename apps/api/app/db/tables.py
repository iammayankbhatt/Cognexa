"""SQLAlchemy Core table definitions mirroring supabase/migrations (the SQL is the source of truth).

tests/test_db_migrations.py reflects the real database and fails if these definitions drift from it.
"""

from __future__ import annotations

from pgvector.sqlalchemy import Vector
from sqlalchemy import (
    BigInteger,
    Boolean,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Integer,
    MetaData,
    Numeric,
    SmallInteger,
    Table,
    Text,
    func,
)
from sqlalchemy.dialects.postgresql import ARRAY, ENUM, JSONB, UUID

EMBEDDING_DIM = 768  # must match vector(768) in migrations and EMBEDDING_DIM in the environment

metadata = MetaData()


def _enum(name: str, *values: str) -> ENUM:
    return ENUM(*values, name=name, create_type=False)


user_role = _enum("user_role", "student", "reviewer", "admin")
study_group = _enum("study_group", "adaptive", "baseline", "none")
question_type = _enum(
    "question_type", "mcq", "multi_select", "true_false", "code_output", "short_answer"
)
quiz_mode = _enum("quiz_mode", "concept", "adaptive", "review", "diagnostic", "pretest", "posttest")
grader = _enum("grader", "auto", "llm")
message_role = _enum("message_role", "user", "assistant", "system")
retrieval_mode = _enum("retrieval_mode", "graphrag", "plain_rag")
report_reason = _enum("report_reason", "incorrect", "incomplete", "off_topic", "harmful", "other")
feedback_status = _enum("feedback_status", "open", "reviewing", "resolved", "dismissed")
proposal_type = _enum("proposal_type", "add_edge", "remove_edge", "tag_chunk", "new_concept")
proposal_status = _enum("proposal_status", "pending", "approved", "rejected")
proposer = _enum("proposer", "llm", "user")
assignment_mode = _enum("assignment_mode", "random", "alternate")


def _now() -> Column:  # type: ignore[type-arg]
    return Column("created_at", DateTime(timezone=True), nullable=False, server_default=func.now())


def _updated() -> Column:  # type: ignore[type-arg]
    return Column("updated_at", DateTime(timezone=True), nullable=False, server_default=func.now())


def _uuid_pk() -> Column:  # type: ignore[type-arg]
    return Column("id", UUID(as_uuid=True), primary_key=True, server_default=func.gen_random_uuid())


profiles = Table(
    "profiles",
    metadata,
    Column("id", UUID(as_uuid=True), primary_key=True),
    Column("display_name", Text),
    Column("role", user_role, nullable=False, server_default="student"),
    Column("theme", Text, nullable=False, server_default="neon-noir"),
    Column("study_group", study_group, nullable=False, server_default="none"),
    Column("onboarding_completed", Boolean, nullable=False, server_default="false"),
    Column("quota_override", JSONB),
    Column("experience_level", Text),
    _now(),
    _updated(),
)

subjects = Table(
    "subjects",
    metadata,
    Column("id", Text, primary_key=True),
    Column("name", Text, nullable=False),
    _now(),
    _updated(),
)

concepts = Table(
    "concepts",
    metadata,
    Column("id", Text, primary_key=True),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("name", Text, nullable=False),
    Column("cluster", Text, nullable=False),
    Column("difficulty", SmallInteger, nullable=False),
    Column("order_index", Integer, nullable=False, server_default="0"),
    _now(),
    _updated(),
)

content_chunks = Table(
    "content_chunks",
    metadata,
    Column("id", Text, primary_key=True),
    Column("concept_id", Text, ForeignKey("concepts.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("kind", Text, nullable=False),
    Column("heading", Text, nullable=False, server_default=""),
    Column("text", Text, nullable=False),
    Column("order", Integer, nullable=False, server_default="0"),
    Column("embedding", Vector(EMBEDDING_DIM)),
    Column("reviewed", Boolean, nullable=False, server_default="false"),
    Column("content_hash", Text),
    Column("embedding_hash", Text),
    Column("embedding_model", Text),
    _now(),
    _updated(),
)

questions = Table(
    "questions",
    metadata,
    Column("id", Text, primary_key=True),
    Column("concept_id", Text, ForeignKey("concepts.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("type", question_type, nullable=False),
    Column("difficulty", SmallInteger, nullable=False),
    Column("prompt", Text, nullable=False),
    Column("code", Text),
    Column("language", Text, nullable=False, server_default="python"),
    Column("options", JSONB),
    Column("answer", JSONB, nullable=False),
    Column("explanation", Text),
    Column("rubric", JSONB),
    Column("misconception_tag", Text),
    Column("diagnoses_prereq", Text, ForeignKey("concepts.id")),
    Column("status", Text, nullable=False, server_default="active"),
    Column("source", Text),
    _now(),
    _updated(),
)

quiz_sessions = Table(
    "quiz_sessions",
    metadata,
    _uuid_pk(),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("mode", quiz_mode, nullable=False),
    Column("concept_id", Text, ForeignKey("concepts.id")),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("submitted_at", DateTime(timezone=True)),
    Column("score", Numeric(8, 3)),
    Column("max_score", Numeric(8, 3)),
    Column("time_limit_s", Integer),
    _now(),
    _updated(),
)

quiz_answers = Table(
    "quiz_answers",
    metadata,
    _uuid_pk(),
    Column("session_id", UUID(as_uuid=True), ForeignKey("quiz_sessions.id"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("question_id", Text, ForeignKey("questions.id"), nullable=False),
    Column("response", JSONB, nullable=False),
    Column("is_correct", Boolean),
    Column("score", Numeric(4, 3)),
    Column("feedback", Text),
    Column("graded_by", grader, nullable=False, server_default="auto"),
    Column("time_ms", Integer),
    _now(),
)

mastery = Table(
    "mastery",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), primary_key=True),
    Column("concept_id", Text, ForeignKey("concepts.id"), primary_key=True),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("score", Numeric(4, 3), nullable=False, server_default="0"),
    Column("attempts", Integer, nullable=False, server_default="0"),
    Column("correct", Integer, nullable=False, server_default="0"),
    Column("last_practiced_at", DateTime(timezone=True)),
    Column("next_review_at", DateTime(timezone=True)),
    Column("ease", Numeric(4, 2), nullable=False, server_default="2.5"),
    _updated(),
)

notes = Table(
    "notes",
    metadata,
    _uuid_pk(),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("concept_id", Text, ForeignKey("concepts.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("body", Text, nullable=False, server_default=""),
    Column("bookmarked", Boolean, nullable=False, server_default="false"),
    _now(),
    _updated(),
)

revision_sheets = Table(
    "revision_sheets",
    metadata,
    _uuid_pk(),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("concept_ids", ARRAY(Text), nullable=False, server_default="{}"),
    Column("content", Text, nullable=False),
    _now(),
)

recommendations_log = Table(
    "recommendations_log",
    metadata,
    _uuid_pk(),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("concept_id", Text, ForeignKey("concepts.id"), nullable=False),
    Column("reason_code", Text, nullable=False),
    Column("reason_text", Text, nullable=False),
    Column("path", JSONB),
    Column("study_group", study_group, nullable=False, server_default="none"),
    Column("shown_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("clicked_at", DateTime(timezone=True)),
    Column("completed_at", DateTime(timezone=True)),
)

chat_threads = Table(
    "chat_threads",
    metadata,
    _uuid_pk(),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("subject_id", Text, ForeignKey("subjects.id"), nullable=False),
    Column("title", Text, nullable=False, server_default="New chat"),
    Column("archived", Boolean, nullable=False, server_default="false"),
    _now(),
    _updated(),
)

chat_messages = Table(
    "chat_messages",
    metadata,
    _uuid_pk(),
    Column("thread_id", UUID(as_uuid=True), ForeignKey("chat_threads.id"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("role", message_role, nullable=False),
    Column("content", Text, nullable=False),
    Column("mode", retrieval_mode),
    Column("matched_concepts", JSONB),
    Column("retrieval_trace", JSONB),
    Column("provider", Text),
    Column("model", Text),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    Column("latency_ms", Integer),
    Column("cached", Boolean, nullable=False, server_default="false"),
    Column("truncated", Boolean, nullable=False, server_default="false"),
    Column("superseded_at", DateTime(timezone=True)),
    Column("reply_to", UUID(as_uuid=True), ForeignKey("chat_messages.id")),
    _now(),
)

message_feedback = Table(
    "message_feedback",
    metadata,
    _uuid_pk(),
    Column("message_id", UUID(as_uuid=True), ForeignKey("chat_messages.id"), nullable=False),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), nullable=False),
    Column("rating", SmallInteger),
    Column("report_reason", report_reason),
    Column("comment", Text),
    Column("status", feedback_status, nullable=False, server_default="open"),
    Column("resolved_by", UUID(as_uuid=True), ForeignKey("profiles.id")),
    Column("resolution_note", Text),
    _now(),
    _updated(),
)

usage_daily = Table(
    "usage_daily",
    metadata,
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id"), primary_key=True),
    Column("date", Date, primary_key=True),
    Column("ai_requests", Integer, nullable=False, server_default="0"),
    Column("tokens_in", BigInteger, nullable=False, server_default="0"),
    Column("tokens_out", BigInteger, nullable=False, server_default="0"),
    Column("est_cost_usd", Numeric(12, 6), nullable=False, server_default="0"),
)

global_usage_daily = Table(
    "global_usage_daily",
    metadata,
    Column("date", Date, primary_key=True),
    Column("ai_requests", Integer, nullable=False, server_default="0"),
    Column("tokens_in", BigInteger, nullable=False, server_default="0"),
    Column("tokens_out", BigInteger, nullable=False, server_default="0"),
)

response_cache = Table(
    "response_cache",
    metadata,
    Column("key_hash", Text, primary_key=True),
    Column("payload", JSONB, nullable=False),
    Column("concept_ids", ARRAY(Text), nullable=False, server_default="{}"),
    _now(),
    Column("expires_at", DateTime(timezone=True), nullable=False),
    Column("hits", Integer, nullable=False, server_default="0"),
    Column("invalidated", Boolean, nullable=False, server_default="false"),
)

graph_proposals = Table(
    "graph_proposals",
    metadata,
    _uuid_pk(),
    Column("type", proposal_type, nullable=False),
    Column("payload", JSONB, nullable=False),
    Column("rationale", Text),
    Column("confidence", Numeric(4, 3)),
    Column("status", proposal_status, nullable=False, server_default="pending"),
    Column("proposed_by", proposer, nullable=False),
    Column("reviewer_id", UUID(as_uuid=True), ForeignKey("profiles.id")),
    Column("decided_at", DateTime(timezone=True)),
    Column("note", Text),
    _now(),
    _updated(),
)

study_settings = Table(
    "study_settings",
    metadata,
    Column("id", SmallInteger, primary_key=True, server_default="1"),
    Column("enabled", Boolean, nullable=False, server_default="false"),
    Column("assignment", assignment_mode, nullable=False, server_default="random"),
    Column("pretest_set_id", Text),
    Column("posttest_set_id", Text),
    Column("started_at", DateTime(timezone=True)),
    _updated(),
)

eval_runs = Table(
    "eval_runs",
    metadata,
    _uuid_pk(),
    Column("name", Text, nullable=False),
    Column("config", JSONB, nullable=False, server_default="{}"),
    Column("summary", JSONB),
    Column("started_at", DateTime(timezone=True), nullable=False, server_default=func.now()),
    Column("finished_at", DateTime(timezone=True)),
    Column("created_by", UUID(as_uuid=True), ForeignKey("profiles.id")),
)

eval_results = Table(
    "eval_results",
    metadata,
    _uuid_pk(),
    Column("run_id", UUID(as_uuid=True), ForeignKey("eval_runs.id"), nullable=False),
    Column("item_id", Text, nullable=False),
    Column("mode", retrieval_mode, nullable=False),
    Column("question", Text, nullable=False),
    Column("answer", Text),
    Column("contexts", JSONB),
    Column("metrics", JSONB),
    Column("latency_ms", Integer),
    Column("tokens_in", Integer),
    Column("tokens_out", Integer),
    _now(),
)

app_settings = Table(
    "app_settings",
    metadata,
    Column("key", Text, primary_key=True),
    Column("value", JSONB, nullable=False),
    _updated(),
    Column("updated_by", UUID(as_uuid=True), ForeignKey("profiles.id")),
)

audit_log = Table(
    "audit_log",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("actor", UUID(as_uuid=True), ForeignKey("profiles.id")),
    Column("action", Text, nullable=False),
    Column("target", Text),
    Column("details", JSONB),
    _now(),
)

llm_calls = Table(
    "llm_calls",
    metadata,
    Column("id", BigInteger, primary_key=True, autoincrement=True),
    Column("user_id", UUID(as_uuid=True), ForeignKey("profiles.id")),
    _now(),
    Column("purpose", Text, nullable=False),
    Column("provider", Text, nullable=False),
    Column("model", Text, nullable=False),
    Column("tokens_in", Integer, nullable=False, server_default="0"),
    Column("tokens_out", Integer, nullable=False, server_default="0"),
    Column("est_cost_usd", Numeric(12, 6), nullable=False, server_default="0"),
    Column("latency_ms", Integer, nullable=False, server_default="0"),
    Column("cached", Boolean, nullable=False, server_default="false"),
    Column("fallback_used", Boolean, nullable=False, server_default="false"),
)

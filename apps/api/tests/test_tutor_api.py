"""Tutor API over HTTP against a throwaway Postgres seeded with the real DSA content.

The graph comes from the in-memory DSA graph (CI's Neo4j starts empty); plain RAG uses the real
pgvector search over the seeded, fake-embedded chunks. Models are the FakeProvider.
"""

from __future__ import annotations

import asyncio
import json
import uuid
from collections.abc import AsyncIterator, Iterator
from dataclasses import dataclass
from typing import Any
from urllib.parse import urlsplit

import asyncpg
import httpx
import pytest

from app.auth.deps import CurrentUser
from app.content.loader import load_chunks, load_questions
from app.content.vectors import embed_pending
from app.core.config import get_settings
from app.db.engine import create_engine, session_factory, to_asyncpg_dsn
from app.db.migrate import apply_migrations
from app.db.repositories import ConceptMirrorRepository, ContentRepository
from app.db.tables import EMBEDDING_DIM
from app.graph.loader import load_subject
from app.graph.memory import InMemoryGraph
from app.llm.embeddings import FakeEmbeddingProvider
from app.llm.errors import FatalLLMError, RetryableLLMError
from app.llm.fake import FakeProvider
from app.llm.router import LLMRouter
from app.tutor.plain_rag import PgVectorSearch
from app.tutor.service import TutorDeps, TutorService, heuristic_title
from tests.conftest import live_settings, requires_postgres
from tests.test_auth_api import Env, env  # noqa: F401

pytestmark = requires_postgres

CANONICAL = (
    "Why does my recursive function crash for big inputs with maximum recursion depth exceeded?"
)
_GRAPH = InMemoryGraph.from_subject("dsa")


class StubGraphProvider:
    configured = True

    def repository(self) -> InMemoryGraph:
        return _GRAPH

    async def close(self) -> None:
        return None


@dataclass
class TEnv:
    env: Env
    app: Any

    @property
    def client(self) -> httpx.AsyncClient:
        return self.env.client

    def set_llm(self, *providers: FakeProvider) -> None:
        async def no_sleep(_: float) -> None:
            return None

        router = LLMRouter(list(providers), sleep=no_sleep)
        self.app.state.llm = router
        deps: TutorDeps = self.app.state.tutor
        self.app.state.tutor = TutorDeps(router, deps.embedder, deps.catalogues, deps.cache)


async def _build_template(url: str) -> None:
    await apply_migrations(url)
    engine = create_engine(url)
    try:
        async with session_factory(engine)() as s:
            async with s.begin():
                await ConceptMirrorRepository(s).upsert_from_file(load_subject("dsa"))
                await ContentRepository(s).upsert_chunks(load_chunks("dsa"))
                await ContentRepository(s).upsert_questions(
                    [("dsa", cid, q) for cid, q in load_questions("dsa")]
                )
            await embed_pending(s, FakeEmbeddingProvider(EMBEDDING_DIM))
    finally:
        await engine.dispose()


async def _admin(url: str) -> asyncpg.Connection:
    return await asyncpg.connect(to_asyncpg_dsn(url), statement_cache_size=0)


@pytest.fixture(scope="module")
def seeded_template() -> Iterator[str]:
    """One migrated database seeded with the DSA concepts and fake-embedded chunks per module;
    each test gets a fast copy (CREATE DATABASE ... TEMPLATE)."""
    url = live_settings().database_url
    if not url:
        pytest.skip("Postgres not configured")
    name = f"cognexa_tpl_{uuid.uuid4().hex[:10]}"

    async def create() -> None:
        try:
            admin = await _admin(url)
        except Exception as exc:
            pytest.skip(f"Postgres not reachable: {type(exc).__name__}")
        try:
            await admin.execute(f'create database "{name}"')
        finally:
            await admin.close()
        await _build_template(urlsplit(url)._replace(path=f"/{name}").geturl())

    async def drop() -> None:
        admin = await _admin(url)
        try:
            await admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity where datname = $1", name
            )
            await admin.execute(f'drop database if exists "{name}"')
        finally:
            await admin.close()

    asyncio.run(create())
    try:
        yield name
    finally:
        asyncio.run(drop())


@pytest.fixture
async def fresh_db_url(seeded_template: str) -> AsyncIterator[str]:
    """Overrides the conftest fixture (used by `env`): a copy of the seeded template."""
    url = live_settings().database_url
    assert url
    name = f"cognexa_t_{uuid.uuid4().hex[:10]}"
    admin = await _admin(url)
    try:
        await admin.execute(f'create database "{name}" template "{seeded_template}"')
    finally:
        await admin.close()
    try:
        yield urlsplit(url)._replace(path=f"/{name}").geturl()
    finally:
        admin = await _admin(url)
        try:
            await admin.execute(
                "select pg_terminate_backend(pid) from pg_stat_activity where datname = $1", name
            )
            await admin.execute(f'drop database if exists "{name}"')
        finally:
            await admin.close()


@pytest.fixture
async def tenv(env: Env) -> AsyncIterator[TEnv]:  # noqa: F811
    app = env.client._transport.app  # type: ignore[attr-defined]
    app.state.graph = StubGraphProvider()
    t = TEnv(env, app)
    t.set_llm(FakeProvider())
    yield t


def parse_sse(body: str) -> list[tuple[str, dict[str, Any]]]:
    events = []
    for block in body.strip().split("\n\n"):
        name = data = None
        for line in block.splitlines():
            if line.startswith("event: "):
                name = line[7:]
            elif line.startswith("data: "):
                data = json.loads(line[6:])
        assert name and data is not None, block
        events.append((name, data))
    return events


async def new_thread(t: TEnv, headers: dict[str, str]) -> str:
    r = await t.client.post("/tutor/threads", headers=headers, json={})
    assert r.status_code == 201, r.text
    return str(r.json()["id"])


async def ask(
    t: TEnv, headers: dict[str, str], thread: str, text: str, mode: str = "graphrag"
) -> list[tuple[str, dict[str, Any]]]:
    r = await t.client.post(
        f"/tutor/threads/{thread}/messages", headers=headers, json={"content": text, "mode": mode}
    )
    assert r.status_code == 200, r.text
    assert r.headers["content-type"].startswith("text/event-stream")
    return parse_sse(r.text)


def last(events: list[tuple[str, dict[str, Any]]], name: str) -> dict[str, Any]:
    return [d for n, d in events if n == name][-1]


# ---------------------------------------------------------------- threads


async def test_thread_crud_pagination_and_isolation(tenv: TEnv) -> None:
    _, ada = await tenv.env.user("ada@example.com")
    _, bob = await tenv.env.user("bob@example.com")
    assert (await tenv.client.get("/tutor/threads")).status_code == 401
    ids = [await new_thread(tenv, ada) for _ in range(3)]
    r = await tenv.client.get("/tutor/threads", headers=ada, params={"page_size": 2})
    page = r.json()
    assert (
        page["total"] == 3 and len(page["items"]) == 2 and page["items"][0]["title"] == "New chat"
    )
    assert (await tenv.client.get("/tutor/threads", headers=bob)).json()["total"] == 0
    # another user's thread does not exist for you
    for method in ("GET", "PATCH", "DELETE"):
        r = await tenv.client.request(method, f"/tutor/threads/{ids[0]}", headers=bob,
                                      json={"title": "x"} if method == "PATCH" else None)  # fmt: skip
        assert r.status_code == 404, method
    # ...and you cannot post into it (no answer is generated, no quota is used)
    r = await tenv.client.post(
        f"/tutor/threads/{ids[0]}/messages", headers=bob, json={"content": "hi there"}
    )
    assert r.status_code == 404
    r = await tenv.client.patch(
        f"/tutor/threads/{ids[0]}",
        headers=ada,
        json={"title": "  Heaps   revision ", "archived": True},
    )
    assert r.json()["title"] == "Heaps revision" and r.json()["archived"] is True
    archived = await tenv.client.get("/tutor/threads", headers=ada, params={"archived": True})
    assert [t["id"] for t in archived.json()["items"]] == [ids[0]]
    found = await tenv.client.get(
        "/tutor/threads", headers=ada, params={"archived": True, "q": "heap"}
    )
    assert found.json()["total"] == 1
    for bad in ({}, {"title": ""}, {"title": "x" * 201}, {"extra": 1}):
        r = await tenv.client.patch(f"/tutor/threads/{ids[1]}", headers=ada, json=bad)
        assert r.status_code == 422, bad
    assert (await tenv.client.delete(f"/tutor/threads/{ids[1]}", headers=ada)).status_code == 204
    assert (await tenv.client.get(f"/tutor/threads/{ids[1]}", headers=ada)).status_code == 404
    r = await tenv.client.post("/tutor/threads", headers=ada, json={"subject_id": "Bad Id"})
    assert r.status_code == 422


def test_heuristic_title() -> None:
    assert heuristic_title("hey, can you explain   binary search trees?") == (
        "Can you explain binary search trees"
    )
    long = heuristic_title("why " * 40)
    assert len(long) <= 61 and long.endswith("…")
    assert heuristic_title("what is a heap") == "What is a heap"


# ---------------------------------------------------------------- messages


async def test_message_stream_order_persistence_and_metering(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, CANONICAL)
    names = [n for n, _ in events]
    assert names[0] == "trace" and names[-1] == "done"
    assert "token" in names and names.index("token") == 1
    tail = names[len(names) - 1 - names[::-1].index("token") + 1 : -1]
    assert tail == ["followups"]  # no `citation` events: chips come from the text
    trace = events[0][1]
    assert trace["summary"].startswith("Function Calls") or "Recursion" in trace["summary"]
    ids = {m["id"] for m in trace["matched"]} | {c["id"] for c in trace["concepts"]}
    assert {"recursion", "call_stack"} <= ids
    assert "call_stack" in {c["concept_id"] for c in trace["chunks"]}

    done = last(events, "done")
    streamed = "".join(d["text"] for n, d in events if n == "token")
    assert done["content"].strip() == streamed.strip() and "<followups>" not in streamed
    assert done["usage"]["provider"] == "fake" and done["usage"]["tokens_out"] > 0

    rows = await tenv.env.db.fetch(
        "select role, content, mode, provider, retrieval_trace, reply_to, id, truncated "
        "from chat_messages where thread_id = $1 order by created_at",
        uuid.UUID(thread),
    )
    assert [r["role"] for r in rows] == ["user", "assistant"]
    assert rows[1]["reply_to"] == rows[0]["id"] and rows[1]["truncated"] is False
    assert rows[1]["provider"] == "fake" and rows[1]["mode"] == "graphrag"
    stored = json.loads(rows[1]["retrieval_trace"])
    assert stored["citations"] and stored["followups"]
    title = await tenv.env.db.fetchval(
        "select title from chat_threads where id = $1", uuid.UUID(thread)
    )
    assert title.startswith("Why does my recursive function crash")
    assert (
        await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
        == 1
    )
    calls = await tenv.env.db.fetch("select purpose from llm_calls where user_id = $1", uid)
    assert len(calls) == done["usage"]["model_calls"] == 3  # classify, controller, answer
    assert {c["purpose"] for c in calls} == {"tutor"}

    view = (await tenv.client.get(f"/tutor/threads/{thread}", headers=h)).json()
    assert [m["role"] for m in view["messages"]] == ["user", "assistant"]
    assert view["messages"][1]["retrieval_trace"]["mode"] == "graphrag"


async def test_off_topic_and_validation(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, "what's the weather like in Paris tomorrow?")
    assert events[0][1]["is_on_topic"] is False
    assert "Data Structures & Algorithms" in last(events, "done")["content"]
    assert await tenv.env.db.fetchval("select count(*) from llm_calls where user_id = $1", uid) == 1
    url = f"/tutor/threads/{thread}/messages"
    assert (await tenv.client.post(url, headers=h, json={"content": ""})).status_code == 422
    assert (
        await tenv.client.post(url, headers=h, json={"content": " " + chr(0x200B) + " "})
    ).status_code == 422
    r = await tenv.client.post(url, headers=h, json={"content": "x" * 3000})
    assert r.status_code == 413 and r.json()["error"]["code"] == "INPUT_TOO_LONG"
    r = await tenv.client.post(f"/tutor/threads/{uuid.uuid4()}/messages", headers=h,
                               json={"content": "what is a heap"})  # fmt: skip
    assert r.status_code == 404
    # failed requests were not charged
    assert (
        await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
        == 1
    )


async def test_response_cache_hit_counts_one_request_no_tokens(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    first = await ask(tenv, h, await new_thread(tenv, h), "What is a hash table?")
    second = await ask(tenv, h, await new_thread(tenv, h), "  what is a hash table ")
    assert last(first, "done")["cached"] is False
    d = last(second, "done")
    assert d["cached"] is True and d["content"] == last(first, "done")["content"]
    assert second[0][1]["cached"] is True
    assert (
        await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
        == 2
    )
    assert await tenv.env.db.fetchval("select count(*) from llm_calls where cached") == 1


async def test_plain_rag_permission_and_pgvector_search(tenv: TEnv) -> None:
    _, student = await tenv.env.user("s@example.com")
    _, reviewer = await tenv.env.user("r@example.com", role="reviewer")
    thread = await new_thread(tenv, student)
    r = await tenv.client.post(
        f"/tutor/threads/{thread}/messages", headers=student,
        json={"content": "what is a linked list", "mode": "plain_rag"},
    )  # fmt: skip
    assert r.status_code == 403 and r.json()["error"]["code"] == "mode_not_allowed"

    rthread = await new_thread(tenv, reviewer)
    events = await ask(tenv, reviewer, rthread, "what is a linked list", mode="plain_rag")
    trace = events[0][1]
    assert trace["mode"] == "plain_rag" and trace["concepts"] == []
    assert 0 < len(trace["chunks"]) <= 6 and all(c["score"] is not None for c in trace["chunks"])

    # an admin can make plain RAG visible to students
    _, admin = await tenv.env.user("boss@example.com", role="admin")
    settings = (await tenv.client.get("/admin/settings", headers=admin)).json()
    features = {**settings["features"], "PLAIN_RAG_VISIBLE_TO_STUDENTS": True}
    assert (
        await tenv.client.put("/admin/settings", headers=admin, json={"features": features})
    ).status_code == 200
    events = await ask(tenv, student, thread, "what is a linked list", mode="plain_rag")
    assert events[0][1]["mode"] == "plain_rag"


async def test_pgvector_search_ranks_by_cosine(tenv: TEnv) -> None:
    search = PgVectorSearch(tenv.app.state.db)
    embedder = FakeEmbeddingProvider(EMBEDDING_DIM)
    vector = (await embedder.embed(["linked list nodes pointers"]))[0]
    hits = await search.search("dsa", vector, 5, embedder.model)
    assert len(hits) == 5
    scores = [s for _, s in hits]
    assert scores == sorted(scores, reverse=True)
    # another embedding model's vectors are never mixed in
    assert await search.search("dsa", vector, 5, "some-other-model") == []


async def test_regenerate_supersedes_latest_answer_only(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    first = last(await ask(tenv, h, thread, "explain binary search"), "done")
    second = last(await ask(tenv, h, thread, "explain merge sort"), "done")
    r = await tenv.client.post(f"/tutor/messages/{first['message_id']}/regenerate", headers=h)
    assert r.status_code == 409
    r = await tenv.client.post(f"/tutor/messages/{second['message_id']}/regenerate", headers=h)
    assert r.status_code == 200, r.text
    regen = last(parse_sse(r.text), "done")
    assert regen["message_id"] != second["message_id"] and regen["cached"] is False
    view = (await tenv.client.get(f"/tutor/threads/{thread}", headers=h)).json()
    assert [m["role"] for m in view["messages"]] == ["user", "assistant", "user", "assistant"]
    assert view["messages"][-1]["id"] == regen["message_id"]
    assert view["messages"][-1]["reply_to"] == view["messages"][2]["id"]
    old = await tenv.env.db.fetchval(
        "select superseded_at from chat_messages where id = $1", uuid.UUID(second["message_id"])
    )
    assert old is not None
    _, bob = await tenv.env.user("bob@example.com")
    r = await tenv.client.post(f"/tutor/messages/{regen['message_id']}/regenerate", headers=bob)
    assert r.status_code == 404
    r = await tenv.client.post(
        f"/tutor/messages/{view['messages'][2]['id']}/edit", headers=bob, json={"content": "mine"}
    )
    assert r.status_code == 404
    user_msg = view["messages"][2]["id"]
    r = await tenv.client.post(f"/tutor/messages/{user_msg}/regenerate", headers=h)
    assert r.status_code == 404
    assert (
        await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
        == 3
    )


async def test_diagnostic_question_then_reply_continues_turn(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    await tenv.env.db.execute(
        "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct) "
        "values ($1, 'call_stack', 'dsa', 0.3, 5, 1)",
        uid,
    )
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, "Why does my recursive function crash?")
    done = last(events, "done")
    assert done["diagnostic"] is True and done["content"].startswith("Quick check:")
    assert events[0][1]["controller"][0]["action"] == "ask_diagnostic"
    assert "call stack" in done["content"].lower()

    events = await ask(tenv, h, thread, "each call adds a stack frame until memory runs out")
    trace = events[0][1]
    assert trace["classification_path"] == "continued"
    assert trace["question"] == "Why does my recursive function crash?"
    assert trace["diagnostic_reply"].startswith("each call adds")
    assert last(events, "done")["diagnostic"] is False
    # the next message is a normal new turn again
    events = await ask(tenv, h, thread, "what is a queue")
    assert events[0][1]["classification_path"] in ("llm", "hybrid")


async def test_quota_is_checked_before_the_stream(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    await tenv.env.db.execute(
        "update profiles set quota_override = '{\"daily_ai_requests\": 1}' where id = $1", uid
    )
    thread = await new_thread(tenv, h)
    await ask(tenv, h, thread, "what is a stack")
    r = await tenv.client.post(f"/tutor/threads/{thread}/messages", headers=h,
                               json={"content": "what is a queue"})  # fmt: skip
    assert r.status_code == 429 and r.json()["error"]["code"] == "QUOTA_EXCEEDED"
    count = await tenv.env.db.fetchval(
        "select count(*) from chat_messages where thread_id = $1", uuid.UUID(thread)
    )
    assert count == 2  # the rejected question was not saved


async def test_model_failure_sends_error_event_and_refunds(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    tenv.set_llm(FakeProvider(script=[FatalLLMError("bad key", status=401)] * 4))
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, "what is a binary heap")
    names = [n for n, _ in events]
    assert names[0] == "trace" and names[-1] == "error"
    assert events[-1][1]["code"] == "llm_unavailable" and events[-1][1]["message_id"] is None
    used = await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
    assert used == 0  # nothing reached the student: refunded


async def test_compare_runs_both_modes(tenv: TEnv) -> None:
    _, student = await tenv.env.user("s@example.com")
    _, reviewer = await tenv.env.user("r@example.com", role="reviewer")
    body = {"question": CANONICAL}
    assert (await tenv.client.post("/tutor/compare", headers=student, json=body)).status_code == 403
    r = await tenv.client.post("/tutor/compare", headers=reviewer, json=body)
    assert r.status_code == 200, r.text
    out = r.json()
    assert out["graphrag"]["trace"]["mode"] == "graphrag"
    assert out["plain_rag"]["trace"]["mode"] == "plain_rag"
    assert "call_stack" in {c["concept_id"] for c in out["graphrag"]["trace"]["chunks"]}
    assert out["graphrag"]["content"] and out["plain_rag"]["content"]


# ---------------------------------------------------------------- disconnects


def _service(t: TEnv) -> TutorService:
    return TutorService(
        db=t.app.state.db,
        settings=t.app.dependency_overrides[get_settings](),
        graph=_GRAPH,
        vectors=PgVectorSearch(t.app.state.db),
        deps=t.app.state.tutor,
        guard=t.app.state.usage_guard,
    )


async def _user_and_thread(t: TEnv) -> tuple[CurrentUser, uuid.UUID]:
    uid, h = await t.env.user("ada@example.com")
    thread = await new_thread(t, h)
    return CurrentUser(id=uid, email="ada@example.com", role="student", profile={}), uuid.UUID(
        thread
    )


async def test_disconnect_saves_partial_answer_as_truncated(tenv: TEnv) -> None:
    user, thread_id = await _user_and_thread(tenv)
    service = _service(tenv)
    prep = await service.prepare(user, thread_id, "explain binary search", "graphrag")
    stream = service.stream(prep)
    tokens = 0
    async for name, _ in stream:
        if name == "token":
            tokens += 1
            if tokens == 3:
                break
    await stream.aclose()  # what Starlette does when the client goes away
    row = await tenv.env.db.fetchrow(
        "select content, truncated, retrieval_trace from chat_messages "
        "where thread_id = $1 and role = 'assistant'",
        thread_id,
    )
    assert row["truncated"] is True and row["content"]
    assert json.loads(row["retrieval_trace"])["truncated"] is True
    # the calls that did finish were metered; the request was not refunded
    assert (
        await tenv.env.db.fetchval(
            "select ai_requests from usage_daily where user_id = $1", user.id
        )
        == 1
    )
    assert (
        await tenv.env.db.fetchval("select count(*) from llm_calls where user_id = $1", user.id)
        == 2
    )


async def test_disconnect_before_any_token_keeps_the_previous_answer(tenv: TEnv) -> None:
    """BUG-053: stopping a regenerate right after the trace event saved an empty truncated
    answer and superseded the good one."""
    user, thread_id = await _user_and_thread(tenv)
    service = _service(tenv)
    prep = await service.prepare(user, thread_id, "explain binary search", "graphrag")
    async for _ in service.stream(prep):
        pass
    old = await tenv.env.db.fetchrow(
        "select id, content from chat_messages where thread_id = $1 and role = 'assistant'",
        thread_id,
    )
    regen = await service.prepare(
        user, thread_id, "explain binary search", "graphrag", regenerate_of=old["id"]
    )
    stream = service.stream(regen)
    async for name, _ in stream:
        if name == "trace":
            break
    await stream.aclose()
    rows = await tenv.env.db.fetch(
        "select id, content, superseded_at from chat_messages "
        "where thread_id = $1 and role = 'assistant'",
        thread_id,
    )
    assert [(r["id"], r["superseded_at"]) for r in rows] == [(old["id"], None)]
    assert all(r["content"] for r in rows)


async def test_concurrent_regenerates_and_edits_leave_one_live_turn(tenv: TEnv) -> None:
    """BUG-054: the 'latest only' checks ran outside the write transaction, so two regenerates
    (two tabs, a retry) both superseded the old answer and both stayed live."""
    _, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, "explain binary search")
    answer_id = last(events, "done")["message_id"]
    url = f"/tutor/messages/{answer_id}/regenerate"
    rs = await asyncio.gather(*[tenv.client.post(url, headers=h) for _ in range(2)])
    assert all(r.status_code in (200, 409) for r in rs), [r.text for r in rs]
    live = await tenv.env.db.fetchval(
        "select count(*) from chat_messages where thread_id = $1 and role = 'assistant' "
        "and superseded_at is null",
        uuid.UUID(thread),
    )
    assert live == 1

    question = await tenv.env.db.fetchval(
        "select id from chat_messages where thread_id = $1 and role = 'user' "
        "and superseded_at is null",
        uuid.UUID(thread),
    )
    edit = f"/tutor/messages/{question}/edit"
    rs = await asyncio.gather(
        *[tenv.client.post(edit, headers=h, json={"content": f"explain heaps {i}"}) for i in (1, 2)]
    )
    assert sorted(r.status_code for r in rs) == [200, 409], [r.text[:200] for r in rs]
    users = await tenv.env.db.fetchval(
        "select count(*) from chat_messages where thread_id = $1 and role = 'user' "
        "and superseded_at is null",
        uuid.UUID(thread),
    )
    assert users == 1


async def test_cancelled_stream_task_still_saves(tenv: TEnv) -> None:
    user, thread_id = await _user_and_thread(tenv)
    tenv.set_llm(FakeProvider(latency_s=0.01))
    service = _service(tenv)
    prep = await service.prepare(user, thread_id, "explain merge sort", "graphrag")
    got_token = asyncio.Event()

    async def consume() -> None:
        async for name, _ in service.stream(prep):
            if name == "token":
                got_token.set()

    task = asyncio.create_task(consume())
    await asyncio.wait_for(got_token.wait(), 10)
    task.cancel()
    with pytest.raises(asyncio.CancelledError):
        await task
    row = await tenv.env.db.fetchrow(
        "select content, truncated from chat_messages where thread_id = $1 and role = 'assistant'",
        thread_id,
    )
    assert row is not None and row["truncated"] is True and row["content"]


async def test_retryable_failure_mid_stream_keeps_partial(tenv: TEnv) -> None:
    from app.llm.fake import FailMidStream

    uid, h = await tenv.env.user("ada@example.com")
    provider = FakeProvider(script=[
        json.dumps({"is_on_topic": True, "concepts": [{"id": "stack", "confidence": 0.9}],
                    "intent": "explain"}),
        json.dumps({"action": "answer_now"}),
        FailMidStream("A stack is a LIFO structure", RetryableLLMError("boom", status=503)),
    ])  # fmt: skip
    tenv.set_llm(provider)
    thread = await new_thread(tenv, h)
    events = await ask(tenv, h, thread, "what is a stack")
    assert events[-1][0] == "error" and events[-1][1]["message_id"]
    row = await tenv.env.db.fetchrow(
        "select content, truncated from chat_messages where id = $1",
        uuid.UUID(events[-1][1]["message_id"]),
    )
    assert row["truncated"] is True and row["content"].startswith("A stack is")
    assert (
        await tenv.env.db.fetchval("select ai_requests from usage_daily where user_id = $1", uid)
        == 1
    )


# ---------------------------------------------------------------- phase 7 backend additions


async def test_feedback_thumbs_report_and_cache_invalidation(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    done = last(await ask(tenv, h, thread, "What is a binary heap?"), "done")
    mid = done["message_id"]
    url = f"/tutor/messages/{mid}/feedback"
    r = await tenv.client.post(url, headers=h, json={"rating": 1})
    assert r.status_code == 200 and r.json() == {"message_id": mid, "rating": 1, "reported": False}
    r = await tenv.client.post(url, headers=h, json={"rating": 0})
    assert r.json()["rating"] is None
    assert (await tenv.client.post(url, headers=h, json={})).status_code == 422
    assert (await tenv.client.post(url, headers=h, json={"rating": 2})).status_code == 422
    bad_reason = {"report": {"reason": "spam"}}
    assert (await tenv.client.post(url, headers=h, json=bad_reason)).status_code == 422

    assert await tenv.env.db.fetchval("select count(*) from response_cache") >= 1
    r = await tenv.client.post(
        url,
        headers=h,
        json={"rating": -1, "report": {"reason": "incorrect", "comment": " wrong  heap "}},
    )
    assert r.json() == {"message_id": mid, "rating": -1, "reported": True}
    row = await tenv.env.db.fetchrow(
        "select rating, report_reason, comment, status from message_feedback where message_id = $1",
        uuid.UUID(mid),
    )
    assert (row["rating"], row["report_reason"], row["comment"], row["status"]) == (
        -1, "incorrect", "wrong heap", "open",
    )  # fmt: skip
    # the reported answer is no longer served from the cache
    again = last(await ask(tenv, h, await new_thread(tenv, h), "What is a binary heap?"), "done")
    assert again["cached"] is False

    view = (await tenv.client.get(f"/tutor/threads/{thread}", headers=h)).json()
    assert view["messages"][1]["feedback"] == {"rating": -1, "reported": True}
    assert view["messages"][0]["feedback"] is None
    _, bob = await tenv.env.user("bob@example.com")
    assert (await tenv.client.post(url, headers=bob, json={"rating": 1})).status_code == 404
    user_msg = view["messages"][0]["id"]
    r = await tenv.client.post(
        f"/tutor/messages/{user_msg}/feedback", headers=h, json={"rating": 1}
    )
    assert r.status_code == 404
    assert uid


async def test_edit_and_resend_replaces_the_last_turn(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    thread = await new_thread(tenv, h)
    await ask(tenv, h, thread, "explain binary search")
    await ask(tenv, h, thread, "explain stacks")
    view = (await tenv.client.get(f"/tutor/threads/{thread}", headers=h)).json()
    first_q, last_q = view["messages"][0]["id"], view["messages"][2]["id"]
    r = await tenv.client.post(f"/tutor/messages/{first_q}/edit", headers=h, json={"content": "x"})
    assert r.status_code == 409
    r = await tenv.client.post(
        f"/tutor/messages/{last_q}/edit", headers=h, json={"content": "explain queues"}
    )
    assert r.status_code == 200, r.text
    events = parse_sse(r.text)
    assert "queue" in [m["id"] for m in events[0][1]["matched"]]
    view = (await tenv.client.get(f"/tutor/threads/{thread}", headers=h)).json()
    contents = [m["content"] for m in view["messages"] if m["role"] == "user"]
    assert contents == ["explain binary search", "explain queues"]
    assert len(view["messages"]) == 4
    hidden = await tenv.env.db.fetchval(
        "select count(*) from chat_messages where thread_id = $1 and superseded_at is not null",
        uuid.UUID(thread),
    )
    assert hidden == 2  # the old question and its answer
    r = await tenv.client.post(f"/tutor/messages/{view['messages'][1]['id']}/edit", headers=h,
                               json={"content": "x"})  # fmt: skip
    assert r.status_code == 404  # an assistant message cannot be edited


async def test_suggestions_follow_the_syllabus(tenv: TEnv) -> None:
    uid, h = await tenv.env.user("ada@example.com")
    r = await tenv.client.get("/tutor/suggestions", headers=h)
    assert r.status_code == 200
    body = r.json()
    assert len(body["starters"]) == 4 and "recursion" in body["starters"][0]["prompt"]
    order = await _GRAPH.topological_order("dsa")
    first = body["continue"]
    assert first["concept_id"] == order[0] and "start" in first["reason"]
    # master the first concept: the next one whose prerequisites are mastered comes up
    await tenv.env.db.execute(
        "insert into mastery (user_id, concept_id, subject_id, score, attempts, correct) "
        "values ($1, $2, 'dsa', 0.9, 5, 5)",
        uid,
        order[0],
    )
    nxt = (await tenv.client.get("/tutor/suggestions", headers=h)).json()["continue"]
    assert nxt["concept_id"] != order[0]
    assert all(p == order[0] for p in _GRAPH.prereqs_of[nxt["concept_id"]])
    assert (await tenv.client.get("/tutor/suggestions", headers=h,
                                  params={"subject_id": "Bad"})).status_code == 422  # fmt: skip


async def test_chunks_endpoint_returns_note_text_in_order(tenv: TEnv) -> None:
    _, h = await tenv.env.user("ada@example.com")
    ids = [c.id for c in _GRAPH.chunks["call_stack"][:2]]
    r = await tenv.client.get("/tutor/chunks", headers=h, params={"ids": [ids[1], ids[0], "nope"]})
    assert r.status_code == 200
    body = r.json()
    assert [c["id"] for c in body] == [ids[1], ids[0]]
    assert body[0]["concept_id"] == "call_stack" and body[0]["text"]
    assert (await tenv.client.get("/tutor/chunks", headers=h)).status_code == 422
    assert (await tenv.client.get("/tutor/chunks", params={"ids": ids})).status_code == 401
